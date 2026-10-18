"""Explicit local operator authorization and read/Stop controls; no polling retry."""
from functools import wraps
from urllib.parse import urlparse
from flask import Blueprint, g, jsonify, request
from ..config import Config
from ..services.workflow_execution import WorkflowLedger, WorkflowHalt, ExecutionScope, _SCOPE, without_execution_scope

GENERATION_ENDPOINTS = {
    'graph.generate_ontology': 'ontology', 'graph.build_graph': 'graph',
    'simulation.prepare_simulation': 'preparation', 'simulation.start_simulation': 'simulation',
    'simulation.run_ensemble': 'simulation', 'simulation.interview_agent': 'interview',
    'simulation.interview_agents_batch': 'interview', 'simulation.interview_all_agents': 'interview',
    'report.generate_report': 'report', 'report.resume_report': 'report',
    'report.regenerate_report_section': 'report', 'report.chat_with_report_agent': 'report_chat',
    'report.create_evidence_proposal': 'proposal',
    'report.continue_evidence_proposal': 'proposal',
    'report.retry_evidence_audit': 'proposal',
}


def control_response(exc):
    return jsonify(success=False, error=exc.reason, error_code=exc.reason,
        workflow_id=exc.workflow_id, terminal=True, recovery_requires_action=True), 409 if exc.workflow_id else 428


def install_workflow_controls(app):
    repository = app.extensions.get('control_db')
    ledger = WorkflowLedger(repository.path) if repository else None
    app.extensions['workflow_ledger'] = ledger
    bp = Blueprint('execution', __name__)

    def configured_identity():
        return dict(provider=Config.LLM_DEFAULT_PROVIDER, model=Config.LLM_MODEL_NAME,
                    base_url=Config.LLM_BASE_URL)

    def cancel_owned(wid, reason, epoch):
        from ..models.task import TaskManager
        from ..services.simulation_runner import SimulationRunner
        from ..services.task_execution import recovery_context
        tasks = TaskManager()
        with tasks.runtime.gate(), without_execution_scope(), recovery_context():
            tasks.runtime.cancel_workflow(wid, reason, epoch=epoch)
            for resource in ledger.resources(wid):
                if resource.startswith('simulation:'):
                    sim_id = resource.split(':', 1)[1]
                    # Never signal a merely recorded/reused PID from another process.
                    state = SimulationRunner.get_run_state(sim_id)
                    run_epoch = (getattr(state, 'execution', None) or {}).get('workflow_epoch')
                    process = SimulationRunner._processes.get(sim_id)
                    locally_running = process and getattr(process, 'poll', lambda: 0)() is None
                    if (sim_id in SimulationRunner._processes and run_epoch == epoch
                            and (state.runner_status.value in {'starting', 'running', 'paused', 'completed'}
                                 or locally_running)):
                          SimulationRunner.stop_simulation(sim_id)

    def stop_owned(wid):
        from ..models.task import TaskManager
        # The transition shares publication/admission's cross-process fence.
        # Earlier guarded publication finishes before Stop can commit; admission
        # is closed before cancellation starts and before any later guard opens.
        with TaskManager().runtime.gate():
            record = ledger.stop(wid)
            cancel_owned(wid, 'stopped', record['epoch'])
            return record

    def authorization_blocker():
        embedding_host = urlparse(Config.EMBEDDING_BASE_URL).hostname
        if Config.EMBEDDING_PROVIDER != 'ollama' or embedding_host not in {'127.0.0.1', 'localhost', '::1', 'host.docker.internal', 'ollama'}:
            return 'remote_embedding_allowance_unsupported'
        if any(getattr(Config, name, 'off') != 'off' for name in
               ('JEV_INTERVIEW_MODE', 'JEV_RERANK_MODE', 'JEV_EVIDENCE_MODE')):
            return 'secondary_provider_allowance_unsupported'
        return None

    @bp.route('/configuration')
    def configuration():
        identity = configured_identity()
        return jsonify(success=True, data=dict(provider=identity['provider'], model=identity['model'],
            controls_available=ledger is not None, configured=bool(Config.LLM_API_KEY),
            embeddings=Config.EMBEDDING_PROVIDER, authorization_blocker=authorization_blocker()))

    @bp.route('/authorize', methods=['POST'])
    def authorize():
        if ledger is None:
            return jsonify(success=False, error='durable_controls_unavailable'), 503
        data = request.get_json() or {}
        identity = configured_identity()
        if data.get('provider') != identity['provider'] or data.get('model') != identity['model']:
            return jsonify(success=False, error='provider_identity_changed'), 409
        blocker = authorization_blocker()
        if blocker:
            return jsonify(success=False, error=blocker), 400
        try:
            resources = data.get('resources', [])
            if not isinstance(resources, list):
                raise ValueError('invalid_resources')
            for resource in resources:
                if not isinstance(resource, str) or ':' not in resource:
                    raise ValueError('invalid_resource')
                kind, identifier = resource.split(':', 1)
                if kind == 'project':
                    from ..models.project import ProjectManager
                    exists = ProjectManager.get_project(identifier)
                elif kind == 'simulation':
                    from ..services.simulation_manager import SimulationManager
                    exists = SimulationManager().get_simulation(identifier)
                elif kind == 'report':
                    from ..services.report_agent import ReportManager
                    exists = ReportManager.get_report(identifier)
                else:
                    raise ValueError('invalid_resource')
                if not exists:
                    raise ValueError('resource_not_found')
            record = ledger.authorize(**identity, request_key=data.get('request_key'),
                input_description=data.get('input_description'), max_requests=data.get('max_requests'),
                max_seconds=data.get('max_seconds'), confirmed=data.get('confirmed'),
                input_fingerprint=data.get('input_fingerprint'), resources=resources,
                consumed_requests=data.get('consumed_requests', 0), spend=data.get('spend'))
            return jsonify(success=True, data=ledger.status(record['workflow_id'])), 201
        except ValueError as exc:
            return jsonify(success=False, error=str(exc)), 400

    @bp.route('/resolve')
    def resolve():
        wid = ledger.resolve(request.args.get('resource', '')) if ledger else None
        return jsonify(success=True, data=dict(workflow_id=wid))

    @bp.route('/<wid>')
    def status(wid):
        try:
            if ledger is None:
                return jsonify(success=False, error='durable_controls_unavailable'), 503
            record = ledger.status(wid)
            if record['state'] in ('stopped', 'runtime_limit'):
                cancel_owned(wid, record['reason'], record['epoch'])
            return jsonify(success=True, data=record)
        except WorkflowHalt as exc:
            return control_response(exc)

    @bp.route('/<wid>/stop', methods=['POST'])
    def stop(wid):
        try:
            if ledger is None:
                return jsonify(success=False, error='durable_controls_unavailable'), 503
            record = stop_owned(wid)
            return jsonify(success=True, data=record)
        except WorkflowHalt as exc:
            return control_response(exc)

    @bp.route('/<wid>/reauthorize', methods=['POST'])
    def reauthorize(wid):
        if ledger is None:
            return jsonify(success=False, error='durable_controls_unavailable'), 503
        data = request.get_json() or {}
        try:
            from ..models.task import TaskManager
            with TaskManager().runtime.gate():
                old_epoch = ledger.status(wid)['epoch']
                record = ledger.reauthorize(wid, max_requests=data.get('max_requests'), max_seconds=data.get('max_seconds'),
                    confirmed=data.get('confirmed'), acknowledge_unknown=data.get('acknowledge_unknown', False),
                    request_key=data.get('request_key'), budget_usd=data.get('budget_usd'))
                if record['epoch'] > old_epoch:
                    cancel_owned(wid, 'authorization_superseded', old_epoch)
            return jsonify(success=True, data=ledger.status(wid))
        except ValueError as exc:
            return jsonify(success=False, error=str(exc)), 400
        except WorkflowHalt as exc:
            return control_response(exc)

    app.register_blueprint(bp, url_prefix='/api/execution')

    @app.before_request
    def bind_request():
        if ledger is None or not request.path.startswith('/api/') or request.path.startswith('/api/execution/'):
            return
        data = request.get_json(silent=True) if request.is_json else request.form
        data = data if isinstance(data, dict) or hasattr(data, 'get') else {}
        values = {**data, **(request.view_args or {})}
        bound = {ledger.resolve(kind + ':' + str(values[key])) for kind, key in
                 [('project', 'project_id'), ('simulation', 'simulation_id'), ('report', 'report_id'), ('graph', 'graph_id')]
                 if values.get(key)} - {None}
        explicit = request.headers.get('X-Workflow-ID') or data.get('workflow_id')
        if len(bound) > 1 or (bound and explicit and explicit not in bound):
            return jsonify(success=False, error='workflow_identity_conflict'), 409
        wid = next(iter(bound), explicit)
        stage = GENERATION_ENDPOINTS.get(request.endpoint)
        g.workflow_id = wid
        try:
            record = ledger.status(wid) if wid else None
            if request.endpoint == 'graph.generate_ontology' and record:
                import hashlib, json
                inputs = []
                for file in request.files.getlist('files'):
                    inputs.append(dict(name=file.filename, sha256=hashlib.sha256(file.read()).hexdigest()))
                    file.stream.seek(0)
                packet = dict(files=inputs, requirement=request.form.get('simulation_requirement', ''),
                              urls=request.form.getlist('urls'))
                digest = hashlib.sha256(json.dumps(packet, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
                if digest != record.get('input_fingerprint'):
                    return jsonify(success=False, error='authorized_input_mismatch'), 409
            if stage:
                from ..models.case import normalize_prediction_settings
                if data.get('prediction_settings'):
                    raw = data.get('prediction_settings')
                    if isinstance(raw, str):
                        import json
                        raw = json.loads(raw)
                    normalize_prediction_settings(raw)
                if data.get('report_mode') and data['report_mode'] not in {'prediction', 'legal_case', 'market_prediction', 'product_risk',
                        'litigation_case', 'motion_only', 'settlement_risk', 'evidence_gap'}:
                    raise ValueError('unsupported_report_mode')
                if data.get('report_depth') and data['report_depth'] not in {'fast', 'standard', 'deep'}:
                    raise ValueError('unsupported_report_depth')
            if stage and (record is None or record['admission_closed']):
                return control_response(WorkflowHalt(record['reason'] if record else 'authorization_required', wid))
            if request.endpoint == 'simulation.stop_simulation' and wid:
                stopped = stop_owned(wid)
                from ..services.simulation_runner import SimulationRunner
                state = SimulationRunner.get_run_state(data.get('simulation_id'))
                return jsonify(success=True, data={**(state.to_dict() if state else {}), 'workflow': stopped})
            # Non-generation endpoints may review existing artifacts, even after
            # Stop. Any unexpected model call there is denied by an empty scope.
            g.workflow_token = _SCOPE.set(ExecutionScope(ledger, wid if stage else None,
                record['epoch'] if record else 0, stage or 'unauthorized_endpoint'))
        except WorkflowHalt as exc:
            return control_response(exc)
        except (ValueError, TypeError) as exc:
            return jsonify(success=False, error=str(exc)), 400

    @app.after_request
    def bind_response(response):
        if request.method != 'POST':
            return response  # Reading an artifact never changes its allowance bindings.
        created_kinds = {
            '/api/graph/ontology/generate': ('project',),
            '/api/simulation/create': ('simulation',),
            '/api/report/generate': ('report',),
        }.get(request.path, ('report',) if request.path.endswith('/accept') else ())
        wid = getattr(g, 'workflow_id', None)
        if ledger and wid and response.status_code < 400 and response.is_json:
            payload = response.get_json(silent=True) or {}
            data = payload.get('data')
            if isinstance(data, dict):
                for kind in created_kinds:
                    if data.get(kind + '_id'):
                        resource = kind + ':' + data[kind + '_id']
                        if ledger.resolve(resource) is None:
                            ledger.bind(wid, resource)
        return response

    @app.teardown_request
    def unbind_request(exc):
        token = getattr(g, 'workflow_token', None)
        if token is not None:
            _SCOPE.reset(token)
            g.workflow_token = None

    # Flask catches Exception, while the control signal must bypass model
    # fallback handlers. Catch it explicitly at each HTTP view boundary.
    def boundary(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            try:
                return view(*args, **kwargs)
            except WorkflowHalt as exc:
                return control_response(exc)
        return wrapped
    for name, view in list(app.view_functions.items()):
        app.view_functions[name] = boundary(view)
