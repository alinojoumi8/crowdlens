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
