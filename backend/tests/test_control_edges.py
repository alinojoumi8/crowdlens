"""Control boundary regressions. Delays/exhaustion are intentional; no inference."""
import json
from types import SimpleNamespace
import pytest
from app.services.workflow_execution import WorkflowLedger, WorkflowHalt, execution_scope
from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
from app.services.ensemble_runner import EnsembleRunner
from test_workflow_execution import authorize
from test_execution_api import controlled, terms
from app.services.task_execution import publication_guard
from app.models.task import TaskManager
from app.services.task_execution import OwnershipLost
from app.storage.control_db import ControlDatabase


def runner(monkeypatch, tmp_path, state, process):
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    for name in ['_graph_memory_enabled','_action_queues','_stdout_files','_stderr_files','_run_states']:
        monkeypatch.setattr(SimulationRunner, name, {})
    monkeypatch.setattr(SimulationRunner,'_repository',None)
    monkeypatch.setattr(SimulationRunner,'_processes',{state.simulation_id:process})
    monkeypatch.setattr(SimulationRunner,'get_run_state',lambda sid:state)
    monkeypatch.setattr(SimulationRunner,'_save_run_state',lambda s:None)


def test_partial_usage_is_unknown_and_known_fields_are_still_measured(tmp_path):
    ledger=WorkflowLedger(tmp_path/'ledger.db');wid=authorize(ledger)
    ticket=ledger.admit(wid,1,'report','synthetic','http://127.0.0.1:1/anthropic')
    ledger.finish(ticket,status='response',usage={'output_tokens':7},http_status=200)
    status=ledger.status(wid)
    assert status['unknown_usage_attempts']==1
    assert status['usage_by_stage']['report']['output_tokens']==7


def test_successful_process_exit_cannot_complete_partial_rounds(tmp_path,monkeypatch):
    state=SimulationRunState('sim_partial',runner_status=RunnerStatus.RUNNING,
        total_rounds=2,current_round=1,twitter_current_round=1,twitter_running=True)
    process=SimpleNamespace(poll=lambda:0,returncode=0)
    runner(monkeypatch,tmp_path,state,process)
    folder=tmp_path/state.simulation_id/'twitter';folder.mkdir(parents=True)
    (folder/'actions.jsonl').write_text(json.dumps({'event_type':'simulation_end','total_rounds':2})+'\n')
    ledger=WorkflowLedger(tmp_path/'ledger.db');wid=authorize(ledger,1)
    ledger.admit(wid,1,'simulation','synthetic','http://127.0.0.1:1/anthropic')
    with execution_scope(ledger,wid,'simulation'):
        SimulationRunner._monitor_simulation(state.simulation_id)
    assert state.runner_status==RunnerStatus.FAILED
    assert state.error=='request_limit'
    assert not state.twitter_completed and state.completed_at is None


def test_late_monitor_does_not_publish_or_clean_replacement(tmp_path,monkeypatch):
    old=SimulationRunState('sim_late',runner_status=RunnerStatus.RUNNING)
    original=SimpleNamespace(poll=lambda:0,returncode=0)
    replacement=SimpleNamespace()
    runner(monkeypatch,tmp_path,old,replacement)
    SimulationRunner._action_queues['sim_late']='new queue'
    SimulationRunner._monitor_simulation('sim_late',original,old)
    assert old.runner_status==RunnerStatus.RUNNING
    assert SimulationRunner._processes['sim_late'] is replacement
    assert SimulationRunner._action_queues['sim_late']=='new queue'


def test_restart_archives_partial_evidence_before_clearing_runtime(tmp_path,monkeypatch):
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path))
    monkeypatch.setattr(SimulationRunner,'_repository',None)
    monkeypatch.setattr(SimulationRunner,'_run_states',{})
    folder=tmp_path/'sim_partial';(folder/'twitter').mkdir(parents=True)
    original=b'{"round":1,"result":"preserved partial"}\n'
    (folder/'twitter'/'actions.jsonl').write_bytes(original)
    (folder/'run_state.json').write_text('{"runner_status":"failed"}')
    result=SimulationRunner.cleanup_simulation_logs('sim_partial')
    assert result['success']
    archive=folder/result['archive']
    assert (archive/'twitter'/'actions.jsonl').read_bytes()==original
    assert (archive/'run_state.json').read_text()=='{"runner_status":"failed"}'
    assert not (folder/'twitter'/'actions.jsonl').exists()


def test_exhausted_ensemble_never_resets_partial_or_starts_next_sample(tmp_path,monkeypatch):
    ledger=WorkflowLedger(tmp_path/'ledger.db');wid=authorize(ledger,1)
    monkeypatch.setattr(EnsembleRunner,'_load_config',lambda sid:{'simulation_requirement':'fictional'})
    calls=[]
    monkeypatch.setattr(EnsembleRunner,'_reset',lambda sid:calls.append('reset'))
    monkeypatch.setattr(SimulationRunner,'start_simulation',lambda **kw:calls.append('start'))
    def partial(*args):
        ledger.admit(wid,1,'simulation','synthetic','http://127.0.0.1:1/anthropic')
        return False
    monkeypatch.setattr(EnsembleRunner,'_wait_for_completion',partial)
    with execution_scope(ledger,wid,'ensemble'),pytest.raises(WorkflowHalt,match='request_limit'):
        EnsembleRunner.run_ensemble('sim_partial',runs=2)
    assert calls==['reset','start']


def test_invalid_resource_authorization_has_no_partial_side_effects(controlled,monkeypatch):
    client,ledger,runtime,calls=controlled
    from app.models.project import ProjectManager
    monkeypatch.setattr(ProjectManager,'get_project',lambda identifier:identifier=='valid')
    response=client.post('/api/execution/authorize',json={**terms(),'resources':['project:valid','project:missing']})
    assert response.status_code==400
    assert ledger.resolve('project:valid') is None
    with ledger.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM workflows').fetchone()[0]==0


def test_stop_transition_serializes_with_publication(controlled,tmp_path):
    import threading
    import time
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    entered=threading.Event();release=threading.Event();stopping=threading.Event();errors=[]
    def publish():
        try:
            with execution_scope(ledger,wid,'report'):
                identifier=TaskManager().create_task('report',resources=[{'key':'report:controlled','root':str(tmp_path)}])
                with TaskManager().attempt(identifier).bind(),publication_guard():
                    entered.set();assert release.wait(5)
                    (tmp_path/'artifact').write_text('authorized publication')
                    TaskManager().complete_task(identifier,{})
        except BaseException as exc: errors.append(exc)
    def stop():
        stopping.set()
        with client.application.test_client() as other:
            assert other.post('/api/execution/'+wid+'/stop',json={}).status_code==200
    worker=threading.Thread(target=publish);worker.start();assert entered.wait(5)
    stopper=threading.Thread(target=stop);stopper.start();assert stopping.wait(5)
    try:
        time.sleep(.05)
        # Stop cannot commit behind an open publication guard. Its linearization
        # occurs after that earlier admitted publication has finished.
        assert ledger.status(wid)['state']=='authorized'
    finally:
        release.set();worker.join(5);stopper.join(5)
    assert not errors
    assert ledger.status(wid)['state']=='stopped'


def test_exhausted_memory_drain_always_releases_runner_resources(tmp_path,monkeypatch):
    from app.services.graph_memory_updater import GraphMemoryManager
    state=SimulationRunState('sim_done',runner_status=RunnerStatus.RUNNING,total_rounds=1,
        twitter_current_round=1,twitter_running=True)
    process=SimpleNamespace(poll=lambda:0,returncode=0)
    runner(monkeypatch,tmp_path,state,process)
    closed=[]
    SimulationRunner._stdout_files[state.simulation_id]=SimpleNamespace(close=lambda:closed.append(True))
    SimulationRunner._action_queues[state.simulation_id]='queue'
    SimulationRunner._graph_memory_enabled[state.simulation_id]=True
    def halted(*args,**kwargs): raise WorkflowHalt('request_limit')
    monkeypatch.setattr(GraphMemoryManager,'stop_updater',halted)
    SimulationRunner._monitor_simulation(state.simulation_id)
    assert state.runner_status==RunnerStatus.COMPLETED
    assert state.simulation_id not in SimulationRunner._processes
    assert state.simulation_id not in SimulationRunner._action_queues
    assert closed==[True]


@pytest.mark.parametrize('kind',['simulation-runtime','ensemble'])
def test_failed_owner_repairs_running_state_without_signalling_recorded_pid(controlled,tmp_path,monkeypatch,kind):
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path/'runs'))
    monkeypatch.setattr(SimulationRunner,'_repository',runtime.repository)
    with execution_scope(ledger,wid,'simulation'):
        task_id=TaskManager().create_task('simulation_run',resources=[{'key':kind+':sim_owned','root':SimulationRunner.RUN_STATE_DIR}])
        owner=TaskManager().attempt(task_id)
        state=SimulationRunState('sim_owned',runner_status=RunnerStatus.RUNNING,process_pid=12345,
            execution={'task_id':task_id,'attempt_id':owner.attempt_id,'workflow_id':wid,'workflow_epoch':1})
        with owner.bind(): SimulationRunner._save_run_state(state)
    signals=[]
    monkeypatch.setattr('app.services.simulation_runner.os.kill',lambda pid,signal:signals.append((pid,signal)))
    assert client.post('/api/execution/'+wid+'/stop',json={}).status_code==200
    SimulationRunner.reconcile_persisted_runs()
    recovered=SimulationRunner.get_run_state('sim_owned')
    assert recovered.runner_status==RunnerStatus.STOPPED
    assert recovered.error=='stopped' and recovered.completed_at is None
    assert runtime.repository.get_simulation_run('sim_owned')['runner_status']=='stopped'
    assert json.loads((tmp_path/'runs'/'sim_owned'/'run_state.json').read_text())['runner_status']=='stopped'
    assert all(signal==0 for _,signal in signals)


def test_replaced_owner_cannot_publish_run_state(controlled,tmp_path,monkeypatch):
    client,ledger,runtime,calls=controlled
    wid=client.post('/api/execution/authorize',json=terms()).json['data']['workflow_id']
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path/'runs'))
    monkeypatch.setattr(SimulationRunner,'_repository',runtime.repository)
    with execution_scope(ledger,wid,'simulation'):
        task_id=TaskManager().create_task('simulation_run',resources=[{'key':'simulation-runtime:sim_owned','root':SimulationRunner.RUN_STATE_DIR}])
        owner=TaskManager().attempt(task_id)
        state=SimulationRunState('sim_owned',runner_status=RunnerStatus.RUNNING,
            execution={'task_id':task_id,'attempt_id':owner.attempt_id})
        with owner.bind(): SimulationRunner._save_run_state(state)
        runtime.update(owner,{'status':'failed','error':'synthetic replacement'})
        replacement=TaskManager().create_task('simulation_run',resources=[{'key':'simulation-runtime:sim_owned','root':SimulationRunner.RUN_STATE_DIR}])
        fresh=SimulationRunState('sim_owned',runner_status=RunnerStatus.RUNNING,
            execution={'task_id':replacement,'attempt_id':TaskManager().attempt(replacement).attempt_id})
        with TaskManager().attempt(replacement).bind(): SimulationRunner._save_run_state(fresh)
        original=(tmp_path/'runs'/'sim_owned'/'run_state.json').read_bytes()
        state.runner_status=RunnerStatus.COMPLETED
        with owner.bind(),pytest.raises(OwnershipLost): SimulationRunner._save_run_state(state)
    assert (tmp_path/'runs'/'sim_owned'/'run_state.json').read_bytes()==original
    assert runtime.repository.get_simulation_run('sim_owned')['execution']['task_id']==replacement


def test_cached_reader_observes_same_attempt_progress_and_completion(controlled,tmp_path,monkeypatch):
    client,ledger,runtime,calls=controlled
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path/'runs'))
    monkeypatch.setattr(SimulationRunner,'_repository',runtime.repository)
    state=SimulationRunState('sim_shared',runner_status=RunnerStatus.RUNNING,current_round=1,
        execution={'task_id':'same','attempt_id':'same'})
    SimulationRunner._save_run_state(state)
    assert SimulationRunner.get_run_state('sim_shared').current_round==1
    data=state.to_detail_dict();data.update(runner_status='completed',current_round=2)
    runtime.repository.put_simulation_run(data)
    refreshed=SimulationRunner.get_run_state('sim_shared')
    assert refreshed.runner_status==RunnerStatus.COMPLETED and refreshed.current_round==2
