"""Disposable Milestone 4 preview: real HTTP/persistence, explicit synthetic adapters.

Never points at a deployment. All outbound provider traffic is disabled. Ontology,
graph extraction/storage and simulation responses are deterministic substitutes;
upload, project/task recovery, proposal and revision endpoints use application code.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
TEXT = 'Alex states that the hearing was postponed until Friday.'
SCOPE = {'graph_id': 'synthetic_graph', 'case_id': 'synthetic_case', 'case_version_id': 'synthetic_v1'}
ONTOLOGY = {'entity_types': [{'name': 'Person', 'description': 'Synthetic participant', 'attributes': []}],
            'edge_types': [], 'analysis_summary': 'Synthetic ontology substitute; no model was called.'}


def configure(output):
    from app.config import Config
    from app.models.project import ProjectManager
    from app.models.case import CaseManager
    from app.models.task import TaskManager
    from app.services.report_agent import ReportManager
    from app.services.simulation_manager import SimulationManager
    from app.storage.control_db import ControlDatabase
    Config.UPLOAD_FOLDER = str(output / 'uploads')
    Config.LLM_API_KEY = 'synthetic-no-provider'
    Config.LLM_MODEL_NAME = 'synthetic-no-provider'
    Config.LLM_DEFAULT_PROVIDER = 'synthetic'
    Config.LLM_BASE_URL = 'http://127.0.0.1:1/anthropic'
    Config.EMBEDDING_PROVIDER = 'ollama'
    Config.EMBEDDING_BASE_URL = 'http://127.0.0.1:11434'
    for key in ['JEV_EVIDENCE_MODE', 'JEV_INTERVIEW_MODE', 'JEV_RERANK_MODE']:
        setattr(Config, key, 'off')
    ProjectManager.PROJECTS_DIR = str(output / 'projects')
    CaseManager.CASES_DIR = str(output / 'cases')
    SimulationManager.SIMULATION_DATA_DIR = str(output / 'simulations')
    ReportManager.REPORTS_DIR = ReportManager.FALLBACK_REPORTS_DIR = str(output / 'reports')
    db = ControlDatabase(output / 'control.db')
    for manager in [ProjectManager, CaseManager, TaskManager]:
        manager.configure_repository(db)
    return db


def seed_abandoned(output):
    database = configure(output)
    from app.models.project import ProjectManager, ProjectStatus
    from app.models.task import TaskManager, TaskStatus
    project = ProjectManager.create_project('Synthetic abandoned graph build')
    project.ontology = ONTOLOGY
    project.simulation_requirement = 'Explore the synthetic hearing record.'
    ProjectManager.save_extracted_text(project.project_id, TEXT)
    manager = TaskManager()
    task_id = manager.create_task('graph_build', metadata={'project_id': project.project_id},
                                 resources=[{'key': 'project:' + project.project_id,
                                             'root': ProjectManager.PROJECTS_DIR}])
    with manager.attempt(task_id).bind():
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=25,
                            message='Synthetic owning process will exit before completion.')
    print(json.dumps({'project_id': project.project_id, 'task_id': task_id}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', required=True, action='store_true')
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--seed-owner', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error('Use a fresh directory beneath the system temporary directory.')
    if args.seed_owner:
        seed_abandoned(output)
        return
    if output.exists():
        parser.error('Output directory must not already exist.')
    frontend = BACKEND.parent / 'frontend' / 'dist'
    if not (frontend / 'index.html').is_file():
        parser.error('Build the current frontend first.')
    output.mkdir(parents=True)
    database = configure(output)
    import requests
    import httpx
    from app.config import Config
    def disabled(*args, **kwargs):
        raise RuntimeError('Provider traffic is disabled in the synthetic browser harness')
    requests.Session.request = disabled
    httpx.Client.send = disabled
    httpx.AsyncClient.send = disabled
    from app.services.report_agent import Report, ReportOutline, ReportSection, ReportStatus, ReportManager
    from app.services.proposal_store import ProposalStore
    from app.models.project import ProjectManager, ProjectStatus
    from app.models.task import TaskManager
    from app.api import graph_bp, report_bp
    import app.api.graph as graph_api
    from flask import Flask, jsonify, request, send_from_directory
    from werkzeug.serving import make_server
    from app.utils.build_identity import runtime_identity
    parent = Report('report_synthetic', 'sim_synthetic', SCOPE['graph_id'],
                    'Review the synthetic hearing record.', ReportStatus.NEEDS_REVIEW,
                    report_mode='legal_case', source_grounding=SCOPE,
                    created_at='2026-10-02T12:00:00',
                    forecast={'status': 'unavailable', 'limitations': 'Synthetic source-only example; no simulation has run.'},
                    outline=ReportOutline('Synthetic hearing report', 'The hearing is Thursday. Other issues remain open.',
                        [ReportSection('Hearing', content='The hearing is Thursday.'),
                         ReportSection('Unrelated contracts', content='Unrelated contracts remain unresolved.')]))
    parent.markdown_content = parent.outline.to_markdown()
    ReportManager.save_report(parent)
    for index, section in enumerate(parent.outline.sections, 1):
        ReportManager.save_section(parent.report_id, index, section)
    progress = {'status': 'needs_review', 'progress': 100, 'completed_sections': [1, 2],
                'total_sections': 2, 'updated_at': '2026-10-02T12:00:00', 'is_stale': False}
    (output / 'reports' / parent.report_id / 'progress.json').write_text(json.dumps(progress))
    project = ProjectManager.create_project('Synthetic seeded report project')
    project.status = ProjectStatus.GRAPH_COMPLETED
    project.graph_id = SCOPE['graph_id']
    project.ontology = ONTOLOGY
    project.simulation_requirement = parent.simulation_requirement
    ProjectManager.save_project(project)
    changed = [False]
    graph = {'graph_id': SCOPE['graph_id'], 'node_count': 1, 'edge_count': 0,
             'nodes': [{'uuid': 'synthetic_alex', 'name': 'Alex', 'labels': ['Entity', 'Person'],
                        'summary': 'Synthetic graph fixture; extraction was not run.'}], 'edges': []}
    class Storage:
        def get_source_chunks(self, **kwargs):
            return [{**SCOPE, 'uuid': 'one', 'document_id': 'synthetic_doc', 'filename': 'synthetic-record.txt',
                     'data': TEXT + (' Updated source.' if changed[0] else ''), 'page': 1, 'chunk_index': 0,
                     'origin': 'source_document'}]
        def get_graph_quality(self, graph_id):
            return {'status': 'unknown', 'safe_to_report': False, 'deductions': []}
    class Ontology:
        def generate(self, **kwargs):
            time.sleep(.25)
            measured('ontology')
            return ONTOLOGY
    class Builder(graph_api.GraphBuilderService):
        def __init__(self, **kwargs):
            self.last_build_profile = {}
        def create_graph(self, **kwargs):
            import uuid
            return 'synthetic_graph_' + uuid.uuid4().hex[:12]
        def set_ontology(self, *args):
            pass
        def add_text_batches(self, graph_id, chunks, **kwargs):
            time.sleep(.35)
            measured('graph')
            return ['one']
        def get_graph_data(self, graph_id):
            return {**graph, 'graph_id': graph_id}
    graph_api.OntologyGenerator = Ontology
    graph_api.GraphBuilderService = Builder
    class LLM:
        model = 'synthetic-no-provider'
        def chat_json(self, messages, **kwargs):
            time.sleep(.2)
            measured('proposal')
            kwargs['usage_callback']('synthetic', self.model, {'input_tokens': 0, 'output_tokens': 0}, 0)
            phase = messages[0]['content'].splitlines()[0]
            if phase == 'EVIDENCE_LEDGER_V1':
                return {'claims': [{'claim_id': 'claim_01', 'kind': 'attributed_allegation', 'text': TEXT,
                    'attribution': 'Alex', 'citation_ids': ['episode:one'], 'premise_claim_ids': [], 'quote': ''}], 'gaps': []}
            if phase == 'EVIDENCE_DRAFT_V1':
                return {'paragraphs': [{'text': TEXT, 'kind': 'attributed_allegation', 'claim_ids': ['claim_01']}],
                    'summary_edits': [{'start': 0, 'end': 24, 'old_text': 'The hearing is Thursday.',
                                      'new_text': TEXT, 'claim_ids': ['claim_01']}]}
            return {'audit_protocol':'target_reviews_v1', 'summary_consistent':True,
                    'paragraph_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic matched source.'}],
                    'summary_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic matched source.'}],
                    'document_reviews':[{'document_id':'synthetic_doc','outcome':'complete','detail':'Synthetic source covered.'}],
                    'claim_reviews': [{'claim_id':'claim_01','outcome':'supported','evidence_ids':['episode:one'],
                        'detail':'Synthetic structural demonstration only; no factual label.'}]}
    app = Flask(__name__, static_folder=None)
    app.config['UPLOAD_FOLDER'] = str(output / 'uploads')
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    store = ProposalStore(ReportManager.REPORTS_DIR)
    app.extensions.update(control_db=database, neo4j_storage=Storage(), evidence_proposal_store=store,
                          evidence_llm_factory=lambda identifier: LLM(), evidence_embedder_factory=lambda: None)
    TaskManager().runtime.start_monitor()
    simulation = {'simulation_id': 'sim_synthetic', 'project_id': project.project_id,
                  'graph_id': SCOPE['graph_id'], 'status': 'ready', 'total_agents': 1,
                  'simulation_requirement': parent.simulation_requirement, 'report_id': parent.report_id,
                  'report_status': 'needs_review', 'created_at': '2026-10-02T12:00:00',
                  'current_round': 2, 'total_rounds': 2, 'files': [{'filename': 'synthetic-record.txt'}]}
    fixture_run = {'sim_synthetic': 'completed', 'sim_control': 'idle'}
    upload_simulation = {}
    control_report = Report('report_interrupted_synthetic', 'sim_control', SCOPE['graph_id'],
        'Synthetic Stop demonstration; no live simulation.', ReportStatus.INTERRUPTED,
        report_mode='prediction', outline=ReportOutline('Interrupted synthetic report',
            'Partial fixture for control testing; no real model was called.', []))
    ReportManager.save_report(control_report)
    (output / 'reports' / control_report.report_id / 'progress.json').write_text(json.dumps({
        'status': 'interrupted', 'progress': 24, 'reason': 'stopped',
        'updated_at': '2026-10-03T00:00:00+00:00', 'completed_sections': [], 'total_sections': 3}))
    @app.route('/api/simulation/<path:rest>', methods=['GET', 'POST'])
    def simulation_fixture(rest):
        if rest == 'history':
            return jsonify(success=True, data=[simulation])
        if rest == 'list':
            return jsonify(success=True, data={'simulations': [simulation]})
        if rest == 'create':
            project_id = (request.get_json() or {}).get('project_id')
            upload_simulation.update({**simulation, 'simulation_id':'sim_upload',
                'project_id':project_id, 'graph_id':ProjectManager.get_project(project_id).graph_id,
                'report_id':None, 'report_status':None})
            return jsonify(success=True, data=upload_simulation)
        if rest == 'prepare':
            return jsonify(success=True, data={'already_prepared': True, **upload_simulation})
        if rest == 'prepare/status':
            return jsonify(success=True, data={'status': 'not_started', 'progress': 0})
        if rest == 'env-status':
            return jsonify(success=True, data={'env_alive': False, 'is_alive': False})
        if rest.endswith('/profiles') or rest.endswith('/profiles/realtime'):
            return jsonify(success=True, data={'profiles': [{'agent_id': 0, 'username': 'synthetic_alex',
                'name': 'Alex', 'bio': 'Synthetic persona fixture.', 'profession': 'Participant', 'entity_type': 'Person',
                'interested_topics': ['hearing']}], 'total_expected': 1})
        if rest.endswith('/config') or rest.endswith('/config/realtime'):
            config = {'time_config': {'total_simulation_hours': 1, 'minutes_per_round': 30},
                'prediction_settings': {'platform': 'twitter', 'memory_mode': 'off', 'seed': 42},
                'seed': 42, 'report_mode': 'prediction', 'report_depth': 'fast',
                'agent_configs': [], 'event_config': {'initial_posts': [], 'scheduled_events': []},
                'reddit_config': {}, 'twitter_config': {}}
            return jsonify(success=True, data={**config, 'config_generated': True, 'config': config})
        if rest.endswith('/run-status') or rest.endswith('/run-status/detail'):
            identifier = rest.split('/')[0]
            wid = ledger.resolve('simulation:' + identifier)
            if wid and ledger.status(wid)['state'] == 'stopped':
                fixture_run[identifier] = 'stopped'
            status = fixture_run.get(identifier, 'completed')
            completed = status == 'completed'
            return jsonify(success=True, data={'simulation_id': identifier, 'runner_status': status,
                'error': 'stopped' if status == 'stopped' else None,
                'status': status, 'twitter_running': status == 'running', 'total_rounds': 2, 'current_round': 2 if completed else 1, 'twitter_current_round': 2 if completed else 1,
                'reddit_current_round': 2 if completed else 0, 'twitter_completed': completed, 'reddit_completed': completed,
                'twitter_actions_count': 1, 'reddit_actions_count': 1, 'recent_actions': [], 'progress_percent': 100})
        if rest in {'start', 'stop', 'close-env'}:
            identifier = (request.get_json() or {}).get('simulation_id', 'sim_synthetic')
            if rest == 'start':
                fixture_run[identifier] = 'running' if identifier == 'sim_control' else 'completed'
            if rest == 'stop':
                fixture_run[identifier] = 'stopped'
                wid = ledger.resolve('simulation:' + identifier)
                if wid:
                    ledger.stop(wid)
            return jsonify(success=True, data={'status':fixture_run[identifier]})
        if rest in {simulation['simulation_id'], 'sim_control', 'sim_upload'}:
            return jsonify(success=True, data=upload_simulation if rest == 'sim_upload' else {**simulation, 'simulation_id': rest})
        if rest.endswith('/actions'):
            return jsonify(success=True, data={'actions': [], 'total': 0})
        if rest.endswith('/timeline'):
            return jsonify(success=True, data={'timeline': []})
        if rest.endswith('/agent-stats'):
            return jsonify(success=True, data={'stats': []})
        return jsonify(success=False, error='synthetic_route_unavailable'), 404
    @app.post('/__synthetic/change-source')
    def change_source():
        changed[0] = not changed[0]
        return jsonify(success=True)
    @app.post('/__synthetic/abandon-task')
    def abandon_task():
        child = subprocess.run([sys.executable, __file__, '--synthetic', '--seed-owner', '--output-dir', str(output)],
                               capture_output=True, text=True, check=True, timeout=15)
        result = json.loads(child.stdout.splitlines()[-1])
        (output / 'abandoned-owner.json').write_text(json.dumps(result, indent=2))
        return jsonify(success=True, data=result)
    def digests():
        return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (output / 'reports' / parent.report_id).iterdir() if path.is_file()}
    original = digests()
    identity = {'source': runtime_identity(), 'git_head': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=BACKEND, text=True).strip(),
        'frontend': {str(path.relative_to(frontend)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in frontend.rglob('*') if path.is_file()},
        'substitutes': ['ontology generator', 'graph builder and storage', 'simulation endpoints', 'drafting LLM'],
        'seeded': ['original report and progress', 'original source chunk', 'graph node', 'simulation history'],
        'provider_calls': 0}
    (output / 'identity.json').write_text(json.dumps(identity, indent=2))
    @app.get('/__synthetic/evidence')
    def evidence():
        result = {**identity, 'parent_unchanged': original == digests(), 'parent_digests': digests(),
                  'reports': [report.to_dict() for report in ReportManager.list_reports()],
                  'proposals': list(store.records()), 'tasks': TaskManager().runtime.records()}
        (output / 'browser-evidence.json').write_text(json.dumps(result, indent=2))
        return jsonify(result)
    @app.get('/')
    @app.get('/<path:path>')
    def frontend_file(path='index.html'):
        if path.startswith('api/'):
            return jsonify(success=False, error='synthetic_route_unavailable'), 404
        return send_from_directory(frontend, path if (frontend / path).is_file() else 'index.html')
    from app.api.execution import install_workflow_controls
    from app.services.workflow_execution import transport_attempt
    install_workflow_controls(app)
    ledger = app.extensions['workflow_ledger']
    def measured(stage):
        with transport_attempt(Config.LLM_MODEL_NAME, Config.LLM_BASE_URL) as receipt:
            receipt.update(http_status=200, usage={'input_tokens':0, 'output_tokens':0})
    for name, resources in [('seeded-report', ['report:report_synthetic','simulation:sim_synthetic']),
                            ('control-demo', ['simulation:sim_control','report:report_interrupted_synthetic'])]:
        root = ledger.authorize(request_key=name, provider='synthetic', model=Config.LLM_MODEL_NAME,
            base_url=Config.LLM_BASE_URL, input_description='Explicitly seeded synthetic browser fixture; no inference',
            max_requests=60, max_seconds=1800, confirmed=True, resources=resources)
    @app.after_request
    def synthetic_notice(response):
        if response.content_type and 'text/html' in response.content_type:
            response.direct_passthrough=False
            response.set_data(response.get_data().replace(b'<body>', b'<body><aside style="padding:8px;background:#fff1bd;color:#312300;font:14px system-ui">SYNTHETIC CONTROL TEST - fixtures replace generation; no external inference or provider charges.</aside>'))
        return response
    server = make_server('127.0.0.1', args.port, app, threaded=True)
    print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}', 'output_dir': str(output)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        TaskManager().runtime.close()


if __name__ == '__main__':
    main()
