"""HTTP lifecycle for persisted evidence proposals; GET never schedules work."""
from functools import wraps
import threading
import time
from flask import current_app, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType
from . import report_bp
from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager
from ..models.case import CaseManager
from ..services.task_execution import OwnershipLost
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


def body(keys, optional=()):
    request.max_content_length = 16384
    value = request.get_json()
    if not isinstance(value, dict) or not set(keys) <= set(value) or not set(value) <= set(keys) | set(optional):
        raise ProposalError('invalid_request', 400)
    return value


def default_embedder():
    if Config.EMBEDDING_PROVIDER != 'ollama':
        from types import SimpleNamespace
        return SimpleNamespace(provider=Config.EMBEDDING_PROVIDER)
    from ..storage.embedding_service import EmbeddingService
    return EmbeddingService(auto_pull=False)


def proposal_source_scope(snapshot, config):
    """Recover legacy general-report scope only from its original graph version."""
    from ..services.source_scope import resolve_source_scope
    return resolve_source_scope(snapshot, config,
        project_loader=ProjectManager.get_project, case_loader=CaseManager.get_case)


def run_worker(store, record, snapshot, lease, budget, storage, llm_factory, embedder_factory, tasks):
    identifier, task_id = record['proposal_id'], record['task_id']
    service = None
    def expire():
        retry_until = time.monotonic() + 1
        while True:
            try:
                store.update(identifier, {'queued', 'running'}, {'state': 'failed', 'error_code': 'deadline_exceeded',
                             'phase': 'deadline', 'usage': budget.snapshot()})
                tasks.fail_task(task_id, 'deadline_exceeded')
                return
            except OwnershipLost:
                return
            except ProposalError as exc:
                if exc.code != 'state_busy' or time.monotonic() >= retry_until:
                    return
                time.sleep(.01)
    watchdog = threading.Timer(budget.remaining(), expire)
    watchdog.daemon = True
    try:
        watchdog.start()
        store.update(identifier, {'queued'}, {'state': 'running', 'phase': 'auditing' if record.get('audit_retry') else 'retrieving'})
        tasks.update_task(task_id, status=TaskStatus.PROCESSING,
            message='Retrying saved audit' if record.get('audit_retry') else 'Drafting from original sources', progress=5)
        service = EvidenceDraftingService(storage, llm_factory(identifier), store,
            embedder=None if record.get('audit_retry') else embedder_factory())
        result = service.generate(identifier, snapshot, budget=budget)
        if result['state'] in {'ready', 'blocked', 'review_pending'}:
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
        try:
            if service is None:
                store.record_telemetry(identifier, usage=budget.snapshot())
        finally:
            lease.close()


@report_bp.route('/<report_id>/evidence-proposals', methods=['POST'])
@endpoint
def create_evidence_proposal(report_id):
    data = body({'section_index', 'request_key'}, optional={'focused_correction', 'summary_selection'})
    if 'summary_selection' in data and ('focused_correction' in data or data['summary_selection'] is None):
        raise ProposalError('invalid_summary_selection', 400)
    if 'focused_correction' in data:
        from ..services.focused_correction import validate_request
        validate_request(data['focused_correction'])
    if type(data['section_index']) is not int or data['section_index'] < 1:
        raise ProposalError('invalid_section', 400)
    store = store_for_app()
    record, lease = store.admit(report_id, data['request_key'], canonical_digest({k: v for k, v in data.items() if k != 'request_key'}))
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
        if 'focused_correction' not in data:
            from ..services.claim_ledger import summary_edit_scope
            try:
                summary_scope = summary_edit_scope(parent.outline.summary,
                    parent.outline.sections[data['section_index'] - 1].content, data.get('summary_selection'))
            except ValueError as exc:
                raise ProposalError(str(exc), 400) from None
            if summary_scope['unmapped_summary_requires_review']:
                raise ProposalError('summary_selection_required', 400)
        try:
            scope = proposal_source_scope(parent.to_dict(), load_simulation_config(parent.simulation_id))
        except ValueError:
            raise ProposalError('missing_or_inconsistent_scope', 409)
        storage = current_app.extensions.get('neo4j_storage')
        if storage is None:
            raise ProposalError('sources_unavailable', 503)
        seconds = min(180, float(current_app.config.get('EVIDENCE_PROPOSAL_SECONDS', 180)))
        budget = DraftBudget(seconds=max(.001, seconds - (time.time() - (record['deadline_at'] - 180))))
        tasks = TaskManager()
        task_id = tasks.create_task('evidence_proposal', metadata={'report_id': report_id, 'proposal_id': record['proposal_id']},
            resources=[{'key':'proposal:'+record['proposal_id'], 'root':str(store.root)}])
        snapshot = parent.to_dict()
        record = store.update(record['proposal_id'], {'queued'}, {'scope': scope, 'section_index': data['section_index'],
            'task_id': task_id, 'deadline_at': time.time() + budget.remaining(),
            **({'summary_selection': data['summary_selection']} if 'summary_selection' in data else {}),
            **({'focused_correction': data['focused_correction']} if 'focused_correction' in data else {})})
        llm_factory = current_app.extensions.get('evidence_llm_factory', lambda identifier: LLMClient())
        embedder_factory = current_app.extensions.get('evidence_embedder_factory', default_embedder)
        tasks.start_task(task_id, run_worker, (store, record, snapshot, lease, budget, storage,
                                  llm_factory, embedder_factory, tasks), name='evidence-proposal')
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
    from ..services.audit_recovery import recovery_details
    store = store_for_app()
    record = store.get(report_id, proposal_id)
    return jsonify(success=True, data={**record, 'audit_recovery': recovery_details(store, record)})


@report_bp.route('/<report_id>/evidence-proposals/<proposal_id>/retry-audit', methods=['POST'])
@endpoint
def retry_evidence_audit(report_id, proposal_id):
    from ..services.audit_recovery import copy_for_retry
    data = body({'request_key', 'recovery_digest'})
    store = store_for_app()
    store.get(report_id, proposal_id)
    record, lease = store.admit(report_id, data['request_key'], canonical_digest({'retry_of': proposal_id, **data}))
    if lease is None:
        return jsonify(success=True, data=record), 202
    handed_off = False
    try:
        original = store.get(report_id, proposal_id)
        changes = copy_for_retry(store, original, record, data['recovery_digest'])
        parent = ReportManager.get_report(report_id)
        if parent is None or canonical_digest(parent.to_dict()) != changes['parent_digest']:
            raise ProposalError('stale_parent')
        storage = current_app.extensions.get('neo4j_storage')
        if storage is None:
            raise ProposalError('sources_unavailable', 503)
        from ..services.source_completeness import freeze_review_sources
        if freeze_review_sources(storage, changes['scope'])['digest'] != changes['source_digest']:
            raise ProposalError('stale_sources')
        seconds = min(180, float(current_app.config.get('EVIDENCE_PROPOSAL_SECONDS', 180)))
        budget = DraftBudget(seconds=max(.001, seconds - (time.time() - (record['deadline_at'] - 180))),
                             previous_usage=original.get('usage'))
        tasks = TaskManager()
        task_id = tasks.create_task('evidence_proposal', metadata={'report_id': report_id, 'proposal_id': record['proposal_id']},
            resources=[{'key': 'proposal:' + record['proposal_id'], 'root': str(store.root)}])
        record = store.update(record['proposal_id'], {'queued'}, {**changes, 'phase': 'auditing',
            'task_id': task_id, 'deadline_at': time.time() + budget.remaining()})
        tasks.start_task(task_id, run_worker, (store, record, parent.to_dict(), lease, budget, storage,
            current_app.extensions.get('evidence_llm_factory', lambda identifier: LLMClient()),
            current_app.extensions.get('evidence_embedder_factory', default_embedder), tasks), name='evidence-proposal')
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


@report_bp.route('/<report_id>/evidence-proposals/<proposal_id>/continue', methods=['POST'])
@endpoint
def continue_evidence_proposal(report_id, proposal_id):
    data = body({'proposal_digest'})
    store = store_for_app()
    store.get(report_id, proposal_id)
    parent = ReportManager.get_report(report_id)
    if parent is None:
        raise ProposalError('not_found', 404)
    storage = current_app.extensions.get('neo4j_storage')
    if storage is None:
        raise ProposalError('sources_unavailable', 503)
    record, lease = store.admit_continuation(report_id, proposal_id, data['proposal_digest'])
    if lease is None:
        return jsonify(success=True, data=record), 202
    handed_off = False
    try:
        seconds = min(180, float(current_app.config.get('EVIDENCE_PROPOSAL_SECONDS', 180)))
        budget = DraftBudget(seconds=max(.001, seconds - (time.time() - (record['deadline_at'] - 180))),
                             previous_usage=record.get('usage'))
        tasks = TaskManager()
        task_id = tasks.create_task('evidence_proposal', metadata={'report_id': report_id, 'proposal_id': proposal_id},
            resources=[{'key': 'proposal:' + proposal_id, 'root': str(store.root)}])
        record = store.update(proposal_id, {'queued'}, {'task_id': task_id, 'deadline_at': time.time() + budget.remaining()})
        tasks.start_task(task_id, run_worker, (store, record, parent.to_dict(), lease, budget, storage,
            current_app.extensions.get('evidence_llm_factory', lambda identifier: LLMClient()),
            current_app.extensions.get('evidence_embedder_factory', default_embedder), tasks), name='evidence-proposal')
        handed_off = True
        return jsonify(success=True, data=record), 202
    except Exception:
        try:
            store.update(proposal_id, {'queued'}, {'state': 'failed', 'error_code': 'admission_failed'})
        except ProposalError:
            pass
        raise
    finally:
        if not handed_off:
            lease.close()


@report_bp.route('/<report_id>/evidence-proposals', methods=['GET'])
@endpoint
def list_evidence_proposals(report_id):
    store = store_for_app()
    store.identifier(report_id)
    records = [{key: row.get(key) for key in ('proposal_id', 'section_index', 'state', 'created_at')}
               for row in store.records() if row['parent_report_id'] == report_id]
    records.sort(key=lambda row: row.get('created_at') or '', reverse=True)
    return jsonify(success=True, data=records)


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
