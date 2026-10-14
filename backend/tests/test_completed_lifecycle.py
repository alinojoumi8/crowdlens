"""Closing admission/idle workers preserves outcomes; all work is provider-free."""
import json
from types import SimpleNamespace

import pytest

from app.models.task import TaskManager
from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
from app.services.task_execution import OwnershipLost
from app.services.workflow_execution import WorkflowHalt, execution_scope
from test_execution_api import controlled, terms
from test_control_edges import runner


@pytest.mark.parametrize('status', [RunnerStatus.COMPLETED, RunnerStatus.FAILED, RunnerStatus.STOPPED])
@pytest.mark.parametrize('exit_code', [0, -15])
def test_idle_stop_and_late_monitor_preserve_outcome(tmp_path, monkeypatch, status, exit_code):
    state = SimulationRunState('sim_terminal', runner_status=status, total_rounds=2,
        current_round=2, twitter_current_round=2, twitter_completed=True,
        completed_at='2026-10-14T01:00:00', error='existing evidence')
    process = SimpleNamespace(poll=lambda: None, returncode=exit_code)
    runner(monkeypatch, tmp_path, state, process)
    terminated = []
    def terminate(*args):
        terminated.append(True)
        process.poll = lambda: exit_code
    monkeypatch.setattr(SimulationRunner, '_terminate_process', terminate)
    folder = tmp_path / state.simulation_id / 'twitter'
    folder.mkdir(parents=True)
    (folder / 'actions.jsonl').write_text(json.dumps({'event_type':'simulation_end'}) + '\n')
    before = state.to_detail_dict()
    SimulationRunner.stop_simulation(state.simulation_id)
    SimulationRunner.stop_simulation(state.simulation_id)
    SimulationRunner._monitor_simulation(state.simulation_id)
    SimulationRunner.stop_simulation(state.simulation_id)
    assert state.to_detail_dict() == before
    assert terminated == [True]
    assert state.simulation_id not in SimulationRunner._processes


@pytest.mark.parametrize('status', [RunnerStatus.STARTING, RunnerStatus.RUNNING, RunnerStatus.PAUSED])
def test_active_stop_cannot_be_completed_by_late_event(tmp_path, monkeypatch, status):
    state = SimulationRunState('sim_active', runner_status=status, total_rounds=2,
        twitter_current_round=2, twitter_running=True)
    process = SimpleNamespace(poll=lambda: None, returncode=0)
    runner(monkeypatch, tmp_path, state, process)
    monkeypatch.setattr(SimulationRunner, '_terminate_process', lambda *args: setattr(process, 'poll', lambda: 0))
    SimulationRunner.stop_simulation(state.simulation_id)
    stopped_at = state.completed_at
    folder = tmp_path / state.simulation_id / 'twitter'
    folder.mkdir(parents=True)
    (folder / 'actions.jsonl').write_text(json.dumps({'event_type':'simulation_end'}) + '\n')
    SimulationRunner._monitor_simulation(state.simulation_id)
    assert state.runner_status == RunnerStatus.STOPPED
    assert state.completed_at == stopped_at
    assert not state.twitter_completed


def test_workflow_stop_preserves_completed_repository_and_fences_late_owner(controlled, tmp_path, monkeypatch):
    client, ledger, runtime, calls = controlled
    wid = client.post('/api/execution/authorize', json=terms()).json['data']['workflow_id']
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path / 'runs'))
    monkeypatch.setattr(SimulationRunner, '_repository', runtime.repository)
    monkeypatch.setattr(SimulationRunner, '_graph_memory_enabled', {})
    ledger.bind(wid, 'simulation:sim_done')
    with execution_scope(ledger, wid, 'simulation'):
        task_id = TaskManager().create_task('simulation_run', resources=[
            {'key':'simulation-runtime:sim_done', 'root':SimulationRunner.RUN_STATE_DIR}])
        owner = TaskManager().attempt(task_id)
        state = SimulationRunState('sim_done', runner_status=RunnerStatus.COMPLETED,
            completed_at='2026-10-14T01:00:00', total_rounds=2, current_round=2,
            twitter_current_round=2, twitter_completed=True,
            execution={'task_id':task_id, 'attempt_id':owner.attempt_id,
                       'workflow_id':wid, 'workflow_epoch':1})
        with owner.bind():
            SimulationRunner._save_run_state(state)
    process = SimpleNamespace(poll=lambda: None)
    SimulationRunner._processes['sim_done'] = process
    terminated = []
    def terminate(*args):
        terminated.append(True)
        process.poll = lambda: -15
    monkeypatch.setattr(SimulationRunner, '_terminate_process', terminate)
    before = runtime.repository.get_simulation_run('sim_done')
    assert client.post('/api/execution/' + wid + '/stop', json={}).status_code == 200
    assert client.post('/api/execution/' + wid + '/stop', json={}).status_code == 200
    assert terminated == [True]
    assert ledger.status(wid)['state'] == 'stopped'
    with pytest.raises(WorkflowHalt):
        ledger.admit(wid, 1, 'simulation', 'synthetic', 'http://127.0.0.1:1/anthropic')
    assert runtime.repository.get_simulation_run('sim_done') == before
    assert json.loads((tmp_path/'runs'/'sim_done'/'run_state.json').read_text()) == before
    state.runner_status = RunnerStatus.FAILED
    with owner.bind(), pytest.raises(OwnershipLost):
        SimulationRunner._save_run_state(state)
    SimulationRunner._run_states.clear()
    assert SimulationRunner.get_run_state('sim_done').runner_status == RunnerStatus.COMPLETED


@pytest.mark.parametrize('status', [RunnerStatus.COMPLETED, RunnerStatus.FAILED, RunnerStatus.STOPPED])
def test_monitor_cleanup_exception_does_not_rewrite_terminal_evidence(tmp_path, monkeypatch, status):
    state = SimulationRunState('sim_error', runner_status=status,
        completed_at='2026-10-14T01:00:00', error='original diagnostic')
    process = SimpleNamespace(poll=lambda: 0, returncode=0)
    runner(monkeypatch, tmp_path, state, process)
    before = state.to_detail_dict()
    def fail_save(state):
        raise OSError('synthetic cleanup failure')
    monkeypatch.setattr(SimulationRunner, '_save_run_state', fail_save)
    SimulationRunner._monitor_simulation(state.simulation_id)
    assert state.to_detail_dict() == before
    assert state.simulation_id not in SimulationRunner._processes


def test_legacy_stop_preserves_completed_simulation_status(monkeypatch):
    from flask import Flask
    from app.api.simulation import simulation_bp
    from app.services.simulation_manager import SimulationManager, SimulationStatus
    state = SimpleNamespace(status=SimulationStatus.COMPLETED)
    monkeypatch.setattr(SimulationRunner, 'stop_simulation', lambda sid:
        SimulationRunState(sid, runner_status=RunnerStatus.COMPLETED))
    monkeypatch.setattr(SimulationManager, 'get_simulation', lambda self, sid: state)
    saves = []
    monkeypatch.setattr(SimulationManager, '_save_simulation_state', lambda *args: saves.append(True))
    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    response = app.test_client().post('/api/simulation/stop', json={'simulation_id':'sim_done'})
    assert response.status_code == 200
    assert response.json['data']['runner_status'] == 'completed'
    assert state.status == SimulationStatus.COMPLETED
    assert saves == []


def test_expired_allowance_closes_idle_completed_worker_without_rewriting_outcome(tmp_path, monkeypatch):
    from app.services.workflow_execution import WorkflowLedger
    from test_workflow_execution import authorize
    state = SimulationRunState('sim_expired', runner_status=RunnerStatus.COMPLETED,
        completed_at='2026-10-14T01:00:00', error='original diagnostic')
    process = SimpleNamespace(poll=lambda: None, returncode=-15)
    runner(monkeypatch, tmp_path, state, process)
    terminated = []
    def terminate(*args):
        terminated.append(True)
        process.poll = lambda: -15
    monkeypatch.setattr(SimulationRunner, '_terminate_process', terminate)
    ledger = WorkflowLedger(tmp_path/'ledger.db')
    wid = authorize(ledger)
    before = state.to_detail_dict()
    with execution_scope(ledger, wid, 'simulation'):
        ledger.stop(wid)
        SimulationRunner._monitor_simulation(state.simulation_id)
    assert terminated == [True]
    assert state.to_detail_dict() == before
    assert state.simulation_id not in SimulationRunner._processes


def test_halt_cannot_terminate_or_remove_replacement_worker(tmp_path, monkeypatch):
    state = SimulationRunState('sim_replaced', runner_status=RunnerStatus.COMPLETED)
    original = SimpleNamespace(poll=lambda: None)
    replacement = SimpleNamespace(poll=lambda: None)
    runner(monkeypatch, tmp_path, state, original)
    terminated = []
    monkeypatch.setattr(SimulationRunner, '_terminate_process', lambda *args: terminated.append(args))
    def halt():
        SimulationRunner._processes[state.simulation_id] = replacement
        raise WorkflowHalt('stopped')
    monkeypatch.setattr('app.services.simulation_runner.current_scope', lambda:
        SimpleNamespace(workflow_id='synthetic', checkpoint=halt))
    SimulationRunner._monitor_simulation(state.simulation_id, original, state)
    assert terminated == []
    assert SimulationRunner._processes[state.simulation_id] is replacement
