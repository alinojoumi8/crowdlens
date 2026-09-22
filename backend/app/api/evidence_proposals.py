"""HTTP lifecycle for persisted evidence proposals; GET never schedules work."""
from functools import wraps
import threading
import time
from flask import current_app, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType
from . import report_bp
from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..services.report_agent import ReportManager, ReportStatus
from ..services.proposal_store import ProposalStore, ProposalError, canonical_digest
from ..services.report_revisions import ReportRevisionService
from ..services.evidence_drafting import EvidenceDraftingService, source_scope
from ..services.forecasting import load_simulation_config
from ..utils.draft_budget import DraftBudget
from ..utils.llm_client import LLMClient


def store_for_app():
    store = current_app.extensions.get('evidence_proposal_store')
    if store is None:
        store = ProposalStore(ReportManager._get_reports_dir())
        current_app.extensions['evidence_proposal_store'] = store
    return store


def endpoint(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ProposalError as exc:
            return jsonify(success=False, error=exc.code), exc.status
        except (BadRequest, UnsupportedMediaType, RequestEntityTooLarge):
            return jsonify(success=False, error='invalid_json'), 400
        except (ValueError, TypeError, KeyError):
            return jsonify(success=False, error='invalid_request'), 400
        except Exception:
            return jsonify(success=False, error='proposal_service_unavailable'), 503
    return wrapped


def body(keys):
    request.max_content_length = 4096
    value = request.get_json()
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ProposalError('invalid_request', 400)
    return value


def default_embedder():
    if Config.EMBEDDING_PROVIDER != 'ollama':
        from types import SimpleNamespace
        return SimpleNamespace(provider=Config.EMBEDDING_PROVIDER)
    from ..storage.embedding_service import EmbeddingService
    return EmbeddingService(auto_pull=False)


def run_worker(store, record, snapshot, lease, budget, storage, llm_factory, embedder_factory, tasks):
    identifier, task_id = record['proposal_id'], record['task_id']
    def expire():
        try:
            store.update(identifier, {'queued', 'running'}, {'state': 'failed', 'error_code': 'deadline_exceeded', 'phase': 'deadline'})
            tasks.fail_task(task_id, 'deadline_exceeded')
        except ProposalError:
            pass
    watchdog = threading.Timer(budget.remaining(), expire)
    watchdog.daemon = True
    try:
        watchdog.start()
        store.update(identifier, {'queued'}, {'state': 'running', 'phase': 'retrieving'})
        tasks.update_task(task_id, status=TaskStatus.PROCESSING, message='Drafting from original sources', progress=5)
        service = EvidenceDraftingService(storage, llm_factory(identifier), store, embedder=embedder_factory())
        result = service.generate(identifier, snapshot, budget=budget)
        if result['state'] in {'ready', 'blocked'}:
            tasks.complete_task(task_id, result={'proposal_id': identifier, 'state': result['state']})
        else:
            tasks.fail_task(task_id, result.get('error_code', result['state']))
    except Exception:
        try:
            store.update(identifier, {'queued', 'running'}, {'state': 'failed', 'error_code': 'drafting_unavailable'})
        except ProposalError:
            pass
        tasks.fail_task(task_id, store.read(identifier).get('error_code', 'drafting_unavailable'))
    finally:
        watchdog.cancel()
        lease.close()


@report_bp.route('/<report_id>/evidence-proposals', methods=['POST'])
@endpoint
def create_evidence_proposal(report_id):
    data = body({'section_index', 'request_key'})
    if type(data['section_index']) is not int or data['section_index'] < 1:
        raise ProposalError('invalid_section', 400)
    store = store_for_app()
    record, lease = store.admit(report_id, data['request_key'], canonical_digest({'section_index': data['section_index']}))
    if lease is None:
        return jsonify(success=True, data=record), 202
    handed_off = False
    try:
        parent = ReportManager.get_report(report_id)
        if parent is None:
            raise ProposalError('not_found', 404)
        if parent.status not in {ReportStatus.COMPLETED, ReportStatus.NEEDS_REVIEW}:
            raise ProposalError('parent_not_terminal')
        if not parent.outline or data['section_index'] > len(parent.outline.sections):
            raise ProposalError('invalid_section', 400)
        try:
            scope = source_scope(parent.to_dict(), load_simulation_config(parent.simulation_id))
        except ValueError:
            raise ProposalError('missing_or_inconsistent_scope', 409)
        storage = current_app.extensions.get('neo4j_storage')
        if storage is None:
            raise ProposalError('sources_unavailable', 503)
        seconds = min(180, float(current_app.config.get('EVIDENCE_PROPOSAL_SECONDS', 180)))
        budget = DraftBudget(seconds=max(.001, seconds - (time.time() - (record['deadline_at'] - 180))))
        tasks = TaskManager()
        task_id = tasks.create_task('evidence_proposal', metadata={'report_id': report_id, 'proposal_id': record['proposal_id']})
        snapshot = parent.to_dict()
        record = store.update(record['proposal_id'], {'queued'}, {'scope': scope, 'section_index': data['section_index'],
            'task_id': task_id, 'deadline_at': time.time() + budget.remaining()})
        llm_factory = current_app.extensions.get('evidence_llm_factory', lambda identifier: LLMClient())
        embedder_factory = current_app.extensions.get('evidence_embedder_factory', default_embedder)
        thread = threading.Thread(target=run_worker, args=(store, record, snapshot, lease, budget, storage,
                                  llm_factory, embedder_factory, tasks), daemon=True, name='evidence-proposal')
        thread.start()
        handed_off = True
        return jsonify(success=True, data=record), 202
    except Exception:
        try:
            store.update(record['proposal_id'], {'queued'}, {'state': 'failed', 'error_code': 'admission_failed'})
        except ProposalError:
            pass
        raise
    finally:
        if not handed_off:
            lease.close()


@report_bp.route('/<report_id>/evidence-proposals/<proposal_id>', methods=['GET'])
@endpoint
def get_evidence_proposal(report_id, proposal_id):
    return jsonify(success=True, data=store_for_app().get(report_id, proposal_id))


def revisions_service():
    return ReportRevisionService(store_for_app(), storage=current_app.extensions.get('neo4j_storage'))


@report_bp.route('/<report_id>/evidence-proposals/<proposal_id>/accept', methods=['POST'])
@endpoint
def accept_evidence_proposal(report_id, proposal_id):
    data = body({'proposal_digest'})
    result = revisions_service().accept(report_id, proposal_id, data['proposal_digest'])
    return jsonify(success=True, data=result.to_dict())


@report_bp.route('/<report_id>/evidence-proposals/<proposal_id>/reject', methods=['POST'])
@endpoint
def reject_evidence_proposal(report_id, proposal_id):
    body(set())
    return jsonify(success=True, data=revisions_service().reject(report_id, proposal_id))


@report_bp.route('/<report_id>/revisions', methods=['GET'])
@endpoint
def list_evidence_revisions(report_id):
    return jsonify(success=True, data=revisions_service().revisions(report_id))
