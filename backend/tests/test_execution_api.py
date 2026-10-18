"""Controlled HTTP/worker/child checks; all providers are fictional fakes."""
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace
import pytest
from flask import Flask, Blueprint, jsonify
from app.api.execution import install_workflow_controls
from app.config import Config
from app.models.task import TaskManager
from app.services.task_execution import TaskRuntime, OwnershipLost, publication_guard
from app.services.workflow_execution import WorkflowLedger, WorkflowHalt, execution_scope, transport_attempt, ipc_authorization
from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
from app.storage.control_db import ControlDatabase


@pytest.fixture
def controlled(tmp_path, monkeypatch):
    repository = ControlDatabase(tmp_path/'control.sqlite')
    runtime = TaskRuntime(repository)
    monkeypatch.setattr(TaskManager, '_repository', repository)
    monkeypatch.setattr(TaskManager, '_runtime', runtime)
    monkeypatch.setattr(Config, 'LLM_DEFAULT_PROVIDER', 'synthetic')
    monkeypatch.setattr(Config, 'LLM_MODEL_NAME', 'synthetic')
    monkeypatch.setattr(Config, 'LLM_BASE_URL', 'http://127.0.0.1:1/anthropic')
    monkeypatch.setattr(Config, 'EMBEDDING_PROVIDER', 'ollama')
    monkeypatch.setattr(Config, 'EMBEDDING_BASE_URL', 'http://127.0.0.1:11434')
    monkeypatch.setattr(SimulationRunner, '_processes', {})
    monkeypatch.setattr(SimulationRunner, '_run_states', {})
    app = Flask(__name__)
    app.extensions['control_db'] = repository
    graph = Blueprint('graph', __name__)
    calls=[]
    @graph.route('/ontology/generate', methods=['POST'])
    def generate_ontology():
        calls.append('ontology')
        with transport_attempt('synthetic', Config.LLM_BASE_URL) as receipt:
            receipt['usage'] = {'input_tokens':3,'output_tokens':2}
            receipt['http_status'] = 200
        return jsonify(success=True,data={'project_id':'project_synthetic'})
    simulation = Blueprint('simulation', __name__)
    @simulation.route('/stop', methods=['POST'])
    def stop_simulation():
        calls.append('legacy Stop view')
        return jsonify(success=True,data={})
    app.register_blueprint(graph,url_prefix='/api/graph')
    app.register_blueprint(simulation,url_prefix='/api/simulation')
    from app.api import report_bp
    app.register_blueprint(report_bp,url_prefix='/api/report')
    install_workflow_controls(app)
    ledger=app.extensions['workflow_ledger']
    yield app.test_client(), ledger, runtime, calls
    runtime.close()


def terms(key='new'):
    packet = dict(files=[dict(name='fixture.md',sha256=hashlib.sha256(b'fictional').hexdigest())],requirement='fictional bike lane',urls=[])
    return dict(provider='synthetic',model='synthetic',request_key=key,input_description='frozen fictional fixture',
        input_fingerprint=hashlib.sha256(json.dumps(packet,separators=(',',':')).encode()).hexdigest(),
        max_requests=4,max_seconds=60,confirmed=True)


def owned_task(runtime, ledger, wid, epoch=1):
    payload=dict(task_id='task_'+str(epoch),task_type='synthetic',status='processing',created_at='2026-10-03T00:00:00+00:00',
        updated_at='2026-10-03T00:00:00+00:00',metadata={'workflow_id':wid,'workflow_epoch':epoch})
    return runtime.admit(payload,[{'key':'simulation-runtime:sim_synthetic','root':'.'}])


def test_http_requires_authorization_and_exact_input(controlled):
    client, ledger, runtime, calls=controlled
    def upload(wid=None, content=b'fictional'):
        return client.post('/api/graph/ontology/generate',data={'files':(io.BytesIO(content),'fixture.md'),
            'simulation_requirement':'fictional bike lane',**({'workflow_id':wid} if wid else {})})
    assert upload().status_code==428
    response=client.post('/api/execution/authorize',json=terms())
    assert response.status_code==201
    wid=response.json['data']['workflow_id']
    assert upload(wid,b'changed').status_code==409
    assert calls==[]
    assert upload(wid).status_code==200
    assert ledger.resolve('project:project_synthetic')==wid
    assert ledger.status(wid)['admitted']==1
    assert client.post('/api/execution/authorize',json=terms()).json['data']['admitted']==1
    assert client.get('/api/execution/'+wid).json['data']['admitted']==1


def test_staged_source_review_requires_open_allowance_and_never_renews_it(controlled, tmp_path, monkeypatch):
    from test_staged_source_review import large_storage, StagedLLM
    from test_source_completeness import generate
    from test_evidence_proposals_api import terminal
    from evidence_draft_samples import sample_report
    from app.services.report_agent import ReportManager
    from app.services.proposal_store import ProposalStore
    client, ledger, runtime, calls = controlled
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path / 'reports'))
    ReportManager.save_report(sample_report())
    record, _ = generate(tmp_path / 'reports', large_storage(), StagedLLM)
    store = ProposalStore(tmp_path / 'reports')
    class Metered(StagedLLM):
        def chat_json(self, *args, **kwargs):
            with transport_attempt('synthetic', Config.LLM_BASE_URL) as receipt:
                receipt['usage'] = {'input_tokens': 20, 'output_tokens': 10}
                receipt['http_status'] = 200
                return super().chat_json(*args, **kwargs)
    client.application.extensions.update(neo4j_storage=large_storage(), evidence_proposal_store=store,
        evidence_llm_factory=lambda identifier: Metered(store, identifier), evidence_embedder_factory=lambda: None)
    url = f"/api/report/report_root/evidence-proposals/{record['proposal_id']}/continue"
    body = {'proposal_digest': record['proposal_digest']}
    assert client.post(url, json=body).status_code == 428
    assert store.read(record['proposal_id'])['state'] == 'review_pending'
    wid = client.post('/api/execution/authorize', json={**terms(), 'max_requests': 1}).json['data']['workflow_id']
    ledger.bind(wid, 'report:report_root')
    assert client.post(url, json=body).status_code == 202
    record = terminal(client, record['proposal_id'])
    assert record['state'] == 'review_pending'
    assert ledger.status(wid)['admitted'] == 1
    assert client.post(url, json={'proposal_digest': record['proposal_digest']}).status_code == 409
    assert store.read(record['proposal_id'])['state'] == 'review_pending'
    assert len(store.read(record['proposal_id'])['source_review']['completed_batches']) == 1
    assert ledger.status(wid)['epoch'] == 1


def test_repeated_stop_and_invalid_or_replayed_reauthorization(controlled,monkeypatch):
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    old=owned_task(runtime,ledger,wid)
    ledger.bind(wid,'simulation:sim_synthetic')
    state=SimulationRunState('sim_synthetic',runner_status=RunnerStatus.RUNNING,execution={'workflow_epoch':1})
    process=SimpleNamespace()
    monkeypatch.setattr(SimulationRunner,'get_run_state',lambda sid:state)
    SimulationRunner._processes['sim_synthetic']=process
    stops=[]
    def stop(sid):
        assert state.runner_status==RunnerStatus.RUNNING
        stops.append(sid);state.runner_status=RunnerStatus.STOPPED
    monkeypatch.setattr(SimulationRunner,'stop_simulation',stop)
    invalid=client.post('/api/execution/'+wid+'/reauthorize',json={'confirmed':False,'request_key':'bad','max_requests':10,'max_seconds':60})
    assert invalid.status_code==400
    runtime.validate(old)
    assert stops==[]
    assert client.post('/api/simulation/stop',json={'simulation_id':'sim_synthetic'}).status_code==200
    assert client.post('/api/execution/'+wid+'/stop',json={}).status_code==200
    assert client.get('/api/execution/'+wid).status_code==200
    assert stops==['sim_synthetic'] and 'legacy Stop view' not in calls
    extension=dict(confirmed=True,request_key='explicit',max_requests=10,max_seconds=60,acknowledge_unknown=True)
    assert client.post('/api/execution/'+wid+'/reauthorize',json=extension).status_code==200
    new=owned_task(runtime,ledger,wid,2)
    state.execution['workflow_epoch']=2; state.runner_status=RunnerStatus.RUNNING
    assert client.post('/api/execution/'+wid+'/reauthorize',json=extension).status_code==200
    runtime.validate(new)
    assert stops==['sim_synthetic']


def test_old_status_cleanup_cannot_cancel_new_epoch(controlled,monkeypatch):
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    owned_task(runtime,ledger,wid)
    ledger.stop(wid)
    original_status=ledger.status
    new=[]
    def race(identifier):
        result=original_status(identifier)
        monkeypatch.setattr(ledger,'status',original_status)
        ledger.reauthorize(wid,max_requests=10,max_seconds=60,confirmed=True,request_key='new_epoch')
        runtime.cancel_workflow(wid,epoch=1)
        new.append(owned_task(runtime,ledger,wid,2))
        return result
    monkeypatch.setattr(ledger,'status',race)
    assert client.get('/api/execution/'+wid).status_code==200
    runtime.validate(new[0])


def test_child_counts_and_stale_owner_rejection_survive_restart(controlled):
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    owner=owned_task(runtime,ledger,wid)
    with execution_scope(ledger,wid,'simulation') as scope, owner.bind():
        env={**os.environ,**scope.child_env()}
    source="""from app.services.workflow_execution import transport_attempt,WorkflowHalt
try:
 with transport_attempt('synthetic','http://127.0.0.1:1/anthropic') as receipt:
  receipt['http_status']=200;receipt['usage']={'input_tokens':1,'output_tokens':1}
except WorkflowHalt as exc:
 print(exc.reason);raise SystemExit(7)
"""
    run=lambda:subprocess.run([sys.executable,'-c',source],env=env,capture_output=True,text=True,timeout=15)
    assert run().returncode==0
    assert WorkflowLedger(ledger.path).status(wid)['admitted']==1
    runtime.cancel_workflow(wid,epoch=1)
    stale=run()
    assert stale.returncode==7 and 'task_ownership_lost' in stale.stdout
    assert ledger.status(wid)['admitted']==1


def test_interviews_reject_legacy_and_old_epoch_environments(controlled,monkeypatch):
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    state=SimulationRunState('sim_synthetic')
    monkeypatch.setattr(SimulationRunner,'get_run_state',lambda sid:state)
    with execution_scope(ledger,wid,'report'):
        with pytest.raises(WorkflowHalt,match='environment_authorization_unavailable'):
            ipc_authorization('sim_synthetic')
        state.execution={'workflow_id':wid,'workflow_epoch':1}
        assert ipc_authorization('sim_synthetic')['epoch']==1
    ledger.reauthorize(wid,max_requests=10,max_seconds=60,confirmed=True,request_key='new')
    with execution_scope(ledger,wid,'report'):
        with pytest.raises(WorkflowHalt,match='environment_authorization_unavailable'):
            ipc_authorization('sim_synthetic')
    assert ledger.status(wid)['admitted']==0


def test_interrupted_progress_prefers_failed_owner_and_preserves_real_errors(controlled,monkeypatch):
    from app.services.report_agent import ReportManager
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    owner=runtime.admit(dict(task_id='report_task',task_type='report_generation',status='processing',
        created_at='2026-10-03T00:00:00+00:00',updated_at='2026-10-03T00:00:00+00:00',progress=24,
        metadata={'workflow_id':wid,'workflow_epoch':1}),[{'key':'report:report_partial','root':'.'}])
    ledger.bind(wid,'report:report_partial')
    runtime.cancel_workflow(wid,'request_limit',epoch=1)
    monkeypatch.setattr(ReportManager,'get_progress',lambda rid:dict(status='generating',progress=24))
    response=client.get('/api/report/report_partial/progress')
    assert response.status_code==200 and response.json['data']['terminal']
    assert response.json['data']['reason']=='request_limit'
    assert response.json['data']['progress']==24
    monkeypatch.setattr(ReportManager,'get_progress',lambda rid:None)
    assert client.get('/api/report/nonexistent/progress').status_code==404
    def invalid(rid): raise OSError('injected unexpected read failure')
    monkeypatch.setattr(ReportManager,'get_progress',invalid)
    assert client.get('/api/report/report_partial/progress').status_code==500


@pytest.mark.parametrize('operation',['resume','section/1/regenerate'])
@pytest.mark.parametrize('depth',['fast','deep'])
def test_recovery_enforces_saved_report_depth(controlled,monkeypatch,operation,depth):
    from app.api import report as api
    from app.services.report_agent import Report, ReportStatus
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    ledger.bind(wid,'report:report_depth')
    saved=Report('report_depth','sim_synthetic','graph_synthetic','fixture',ReportStatus.INTERRUPTED,report_depth=depth)
    monkeypatch.setattr(api.ReportManager,'get_report',lambda rid:saved)
    monkeypatch.setattr(api,'GraphToolsService',lambda **kw:object())
    client.application.extensions['neo4j_storage']=object()
    seen=[]
    class Agent:
        def __init__(self,**kw):seen.append(kw)
        def resume_report(self,report,**kw):return report
        def regenerate_section(self,report,**kw):seen.append(kw);return report
    monkeypatch.setattr(api,'ReportAgent',Agent)
    def start(self,identifier,function,*a,**kw):
        with self.attempt(identifier).bind():function()
    monkeypatch.setattr(TaskManager,'start_task',start)
    response=client.post('/api/report/report_depth/'+operation,json={})
    assert response.status_code==200,response.json
    assert seen[0]['report_depth']==depth
    if operation!='resume':assert seen[1]['disable_interviews'] is (depth=='fast')


def test_pending_recovery_returns_queued_instead_of_old_interruption(controlled,monkeypatch):
    from app.services.report_agent import ReportManager
    client,ledger,runtime,calls=controlled
    runtime.admit(dict(task_id='replacement',task_type='report_resume',status='pending',
        created_at='2026-10-03T00:00:00+00:00',updated_at='2026-10-03T00:00:00+00:00'),
        [{'key':'report:partial','root':'.'}])
    monkeypatch.setattr(ReportManager,'get_progress',lambda rid:dict(status='interrupted',progress=24))
    response=client.get('/api/report/partial/progress')
    assert response.status_code==200
    assert response.json['data']['effective_status']=='queued'
    assert response.json['data']['terminal'] is False


def test_reading_report_never_rebinds_another_workflows_shared_graph(controlled,monkeypatch):
    from app.services.report_agent import ReportManager,Report,ReportStatus
    client,ledger,runtime,calls=controlled
    first=client.post('/api/execution/authorize',json=terms('first')).json['data']['workflow_id']
    second=client.post('/api/execution/authorize',json=terms('second')).json['data']['workflow_id']
    ledger.bind(first,'graph:shared');ledger.bind(second,'report:readonly')
    report=Report('readonly','sim_readonly','shared','fictional',ReportStatus.INTERRUPTED)
    monkeypatch.setattr(ReportManager,'get_report',lambda rid:report)
    assert client.get('/api/report/readonly').status_code==200
    assert ledger.resolve('graph:shared')==first
    assert ledger.resolve('simulation:sim_readonly') is None


def test_recovery_response_does_not_rebind_existing_related_resources(controlled,monkeypatch,tmp_path):
    from app.services.report_agent import ReportManager,Report,ReportStatus
    client,ledger,runtime,calls=controlled
    first=client.post('/api/execution/authorize',json=terms('first')).json['data']['workflow_id']
    second=client.post('/api/execution/authorize',json=terms('second')).json['data']['workflow_id']
    ledger.bind(first,'simulation:shared');ledger.bind(first,'graph:shared');ledger.bind(second,'report:recovery')
    report=Report('recovery','shared','shared','fictional',ReportStatus.INTERRUPTED)
    monkeypatch.setattr(ReportManager,'REPORTS_DIR',str(tmp_path/'reports'))
    monkeypatch.setattr(ReportManager,'get_report',lambda rid:report)
    monkeypatch.setattr('app.api.report.GraphToolsService',lambda **kw:object())
    client.application.extensions['neo4j_storage']=object()
    class Agent:
        def __init__(self,**kw):pass
        def resume_report(self,report,**kw):return report
    monkeypatch.setattr('app.api.report.ReportAgent',Agent)
    def start(self,identifier,function,*a,**kw):
        with self.attempt(identifier).bind():function()
    monkeypatch.setattr(TaskManager,'start_task',start)
    response=client.post('/api/report/recovery/resume',json={})
    assert response.status_code==200
    assert ledger.resolve('simulation:shared')==first and ledger.resolve('graph:shared')==first
    assert ledger.status(second)['admitted']==0


@pytest.mark.parametrize('mode', ['JEV_INTERVIEW_MODE', 'JEV_RERANK_MODE', 'JEV_EVIDENCE_MODE'])
def test_configuration_explains_secondary_provider_blocker(controlled, monkeypatch, mode):
    client, ledger, runtime, calls = controlled
    for name in ('JEV_INTERVIEW_MODE', 'JEV_RERANK_MODE', 'JEV_EVIDENCE_MODE'):
        monkeypatch.setattr(Config, name, 'off')
    monkeypatch.setattr(Config, mode, 'shadow')
    assert client.get('/api/execution/configuration').json['data']['authorization_blocker'] == 'secondary_provider_allowance_unsupported'
    response = client.post('/api/execution/authorize', json=terms())
    assert response.status_code == 400
    assert response.json['error'] == 'secondary_provider_allowance_unsupported'
    assert calls == []
    monkeypatch.setattr(Config, mode, 'off')
    assert client.get('/api/execution/configuration').json['data']['authorization_blocker'] is None
    assert client.post('/api/execution/authorize', json=terms()).status_code == 201


def test_http_spend_terms_and_renewal_are_explicit_and_persisted(controlled):
    client, ledger, runtime, calls = controlled
    data = terms('usd')
    data['spend'] = dict(currency='USD', budget_usd='1', reserve_usd='0.1',
        input_usd_per_million='1', output_usd_per_million='2', price_reference='Fictional v1')
    response = client.post('/api/execution/authorize', json=data)
    assert response.status_code == 201
    wid = response.json['data']['workflow_id']
    assert response.json['data']['spend']['budget_micro_usd'] == 1_000_000
    assert client.post('/api/execution/authorize', json=data).json['data']['workflow_id'] == wid
    altered = {**data, 'spend': {**data['spend'], 'budget_usd':'2'}}
    assert client.post('/api/execution/authorize', json=altered).status_code == 400
    ticket = ledger.admit(wid, 1, 'report', 'synthetic', Config.LLM_BASE_URL)
    ledger.finish(ticket, status='response', usage={'input_tokens':3,'output_tokens':2})
    client.post('/api/execution/'+wid+'/stop')
    renew = dict(max_requests=5, max_seconds=60, confirmed=True, request_key='renew-usd')
    assert client.post('/api/execution/'+wid+'/reauthorize', json=renew).json['error'] == 'explicit_spend_budget_required'
    response = client.post('/api/execution/'+wid+'/reauthorize', json={**renew, 'budget_usd':'1'})
    assert response.status_code == 200
    assert response.json['data']['spend']['estimated_micro_usd'] == 7
    assert client.get('/api/execution/'+wid).json['data']['spend']['price_reference'] == 'Fictional v1'
    assert calls == []


def test_saved_audit_retry_keeps_unknown_attempt_and_request_limit(controlled, tmp_path, monkeypatch):
    import requests
    from test_evidence_drafting import FakeLLM, SourceStorage, run
    from test_evidence_proposals_api import terminal
    from evidence_draft_samples import sample_report
    from app.services.report_agent import ReportManager
    from app.services.audit_recovery import recovery_details
    client, ledger, runtime, calls = controlled
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path / 'reports'))
    ReportManager.save_report(sample_report())
    original = FakeLLM.chat_json
    def timeout(self, messages, **kwargs):
        if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
            raise requests.Timeout('fictional timeout')
        return original(self, messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', timeout)
    failed, llm = run(tmp_path / 'reports')
    monkeypatch.setattr(FakeLLM, 'chat_json', original)
    store = llm.store
    class Metered(FakeLLM):
        def chat_json(self, messages, **kwargs):
            assert messages[0]['content'].startswith('EVIDENCE_AUDIT_V1')
            with transport_attempt('synthetic', Config.LLM_BASE_URL) as receipt:
                receipt.update(usage={'input_tokens': 20, 'output_tokens': 10}, http_status=200)
                return super().chat_json(messages, **kwargs)
    client.application.extensions.update(neo4j_storage=SourceStorage(), evidence_proposal_store=store,
        evidence_llm_factory=lambda identifier: Metered(store, identifier), evidence_embedder_factory=lambda: None)
    url = f"/api/report/report_root/evidence-proposals/{failed['proposal_id']}/retry-audit"
    body = {'request_key': 'retry', 'recovery_digest': recovery_details(store, failed)['digest']}
    before = list(store.records())
    assert client.post(url, json=body).status_code == 428
    assert list(store.records()) == before
    wid = client.post('/api/execution/authorize', json={**terms(), 'max_requests': 2}).json['data']['workflow_id']
    ledger.bind(wid, 'report:report_root')
    # The original timed-out delivery still occupies a request in this ledger.
    with execution_scope(ledger, wid, 'proposal'):
        with pytest.raises(requests.Timeout), transport_attempt('synthetic', Config.LLM_BASE_URL):
            raise requests.Timeout('fictional earlier delivery')
    response = client.post(url, json=body)
    assert response.status_code == 202
    recovered = terminal(client, response.json['data']['proposal_id'])
    assert recovered['state'] == 'ready'
    status = ledger.status(wid)
    assert status['admitted'] == 2 and status['unknown_usage_attempts'] == 1 and status['epoch'] == 1
    assert client.post(url, json={**body, 'request_key': 'over-limit'}).status_code == 409
    ledger.stop(wid)
    response = client.post(url, json={**body, 'request_key': 'stopped'})
    assert response.status_code == 409 and response.json['error'] == 'stopped'
    assert ledger.status(wid)['admitted'] == 2
