import json
import pytest

from app.services.simulation_runner import RunnerStatus, SimulationRunState, SimulationRunner
from app.storage.control_db import ControlDatabase


def _reset_runner():
    SimulationRunner.configure_repository(None)
    SimulationRunner._run_states.clear()


def test_run_state_is_restored_from_sqlite_and_json_is_only_a_compatibility_mirror(tmp_path, monkeypatch):
    database = ControlDatabase(tmp_path / "control.db")
    run_dir = tmp_path / "simulations"
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(run_dir))
    SimulationRunner.configure_repository(database)
    SimulationRunner._run_states.clear()
    try:
        state = SimulationRunState(
            simulation_id="sim_1",
            runner_status=RunnerStatus.RUNNING,
            current_round=3,
            process_pid=123,
        )
        SimulationRunner._save_run_state(state)

        mirror = run_dir / "sim_1" / "run_state.json"
        assert json.loads(mirror.read_text(encoding="utf-8"))["current_round"] == 3
        database.put_simulation_run({**database.get_simulation_run("sim_1"), "current_round": 7})
        SimulationRunner._run_states.clear()

        restored = SimulationRunner.get_run_state("sim_1")

        assert restored.current_round == 7
    finally:
        _reset_runner()


def test_reconciliation_marks_missing_recorded_process_as_interrupted(tmp_path, monkeypatch):
    database = ControlDatabase(tmp_path / "control.db")
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations"))
    SimulationRunner.configure_repository(database)
    SimulationRunner._run_states.clear()
    database.put_simulation_run({
        "simulation_id": "sim_orphan",
        "runner_status": "running",
        "process_pid": 999999,
        "updated_at": "2026-01-01T00:00:00",
    })

    def missing_process(pid, signal_number):
        del pid, signal_number
        raise ProcessLookupError("gone")

    monkeypatch.setattr("os.kill", missing_process)
    try:
        result = SimulationRunner.reconcile_persisted_runs()

        restored = database.get_simulation_run("sim_orphan")
        assert result == {"checked": 1, "alive": 0, "interrupted": 1, "unknown": 0}
        assert restored["runner_status"] == "stopped"
        assert restored["process_pid"] is None
        assert "interrupted during backend restart" in restored["error"].lower()
    finally:
        _reset_runner()


def test_reconciliation_keeps_live_recorded_process_running(tmp_path, monkeypatch):
    database = ControlDatabase(tmp_path / "control.db")
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations"))
    SimulationRunner.configure_repository(database)
    SimulationRunner._run_states.clear()
    database.put_simulation_run({
        "simulation_id": "sim_live",
        "process_identity": {"birth": "synthetic-current-process"},
        "runner_status": "running",
        "process_pid": 123,
        "updated_at": "2026-01-01T00:00:00",
    })
    monkeypatch.setattr("os.kill", lambda pid, signal_number: None)
    monkeypatch.setattr("app.utils.process_identity.process_identity", lambda pid: {"birth":"synthetic-current-process"})
    try:
        result = SimulationRunner.reconcile_persisted_runs()

        assert result == {"checked": 1, "alive": 1, "interrupted": 0, "unknown": 0}
        assert database.get_simulation_run("sim_live")["runner_status"] == "running"
    finally:
        _reset_runner()


def test_cleanup_removes_authoritative_state_even_without_artifact_directory(tmp_path, monkeypatch):
    database = ControlDatabase(tmp_path / "control.db")
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations"))
    SimulationRunner.configure_repository(database)
    database.put_simulation_run({"simulation_id": "sim_old", "runner_status": "completed"})
    try:
        assert SimulationRunner.cleanup_simulation_logs("sim_old")["success"]
        assert SimulationRunner.get_run_state("sim_old") is None
    finally:
        _reset_runner()


def test_cleanup_removes_previous_forecast_and_agent_memories(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
    sim_dir = tmp_path / "sim_old"
    sim_dir.mkdir()
    names = ("ensemble_signal.json", "agent_short_memory.json", "agent_memory_summaries.json")
    for name in names:
        (sim_dir / name).write_text('{}')
    (sim_dir / "simulation_config.json").write_text('{}')
    assert SimulationRunner.cleanup_simulation_logs("sim_old")["success"]
    assert all(not (sim_dir / name).exists() for name in names)
    assert (sim_dir / "simulation_config.json").exists()


@pytest.mark.parametrize('recorded, observed, expected', [
    ({'birth':'old'}, {'birth':'reused'}, 'interrupted'),
    (None, {'birth':'current'}, 'unknown'),
    ({'birth':'old'}, None, 'unknown'),
])
def test_restart_never_adopts_or_signals_an_unowned_pid(tmp_path, monkeypatch, recorded, observed, expected):
    database=ControlDatabase(tmp_path/'control.db')
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path/'simulations'))
    SimulationRunner.configure_repository(database);SimulationRunner._run_states.clear()
    database.put_simulation_run({'simulation_id':'sim_pid','runner_status':'running','process_pid':123,'process_identity':recorded})
    signals=[]
    monkeypatch.setattr('os.kill',lambda pid,signal:signals.append(signal))
    monkeypatch.setattr('app.utils.process_identity.process_identity',lambda pid:observed)
    try:
        result=SimulationRunner.reconcile_persisted_runs()
        assert result[expected]==1 and result['alive']==0
        saved=database.get_simulation_run('sim_pid')
        assert saved['execution']['restart_recovery']['recorded_identity']==recorded
        assert signals==[0]
        assert saved['runner_status']==('stopped' if expected=='interrupted' else 'running')
    finally:_reset_runner()


@pytest.mark.parametrize('failure',['database','mirror'])
def test_failed_state_write_preserves_old_mirror_and_authoritative_recovery(tmp_path,monkeypatch,failure):
    import errno
    database=ControlDatabase(tmp_path/'control.db')
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path/'simulations'))
    SimulationRunner.configure_repository(database);SimulationRunner._run_states.clear()
    try:
        old=SimulationRunState(simulation_id='sim_write',current_round=3)
        SimulationRunner._save_run_state(old)
        mirror=tmp_path/'simulations/sim_write/run_state.json';before=mirror.read_bytes()
        new=SimulationRunState(simulation_id='sim_write',current_round=4)
        def full(*a,**k):raise OSError(errno.ENOSPC,'synthetic full disk')
        if failure=='database':monkeypatch.setattr(database,'put_simulation_run',full)
        else:monkeypatch.setattr('os.replace',full)
        with pytest.raises(OSError):SimulationRunner._save_run_state(new)
        assert mirror.read_bytes()==before
        assert not list(mirror.parent.glob('.run_state.*.tmp'))
        SimulationRunner._run_states.clear()
        assert SimulationRunner.get_run_state('sim_write').current_round==(3 if failure=='database' else 4)
    finally:_reset_runner()


def test_restart_preserves_a_current_task_owner_without_failing_startup(tmp_path, monkeypatch):
    from app.models.task import TaskManager
    database=ControlDatabase(tmp_path/'control.db')
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path/'simulations'))
    SimulationRunner.configure_repository(database);TaskManager.configure_repository(database)
    payload={'simulation_id':'sim_owned','runner_status':'running','process_pid':999999}
    database.put_simulation_run(payload)
    TaskManager().runtime.admit({'task_id':'current_owner','status':'processing'},[{'key':'simulation-runtime:sim_owned','root':str(tmp_path/'simulations')}])
    def gone(*args):raise ProcessLookupError()
    monkeypatch.setattr('os.kill',gone)
    try:
        result=SimulationRunner.reconcile_persisted_runs()
        assert result['unknown']==1 and result['interrupted']==0
        assert database.get_simulation_run('sim_owned')==payload
    finally:
        TaskManager.configure_repository(None);_reset_runner()


def test_restart_cannot_overwrite_a_newer_completion(tmp_path,monkeypatch):
    database=ControlDatabase(tmp_path/'control.db')
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path/'simulations'))
    SimulationRunner.configure_repository(database)
    payload={'simulation_id':'sim_race','runner_status':'running','process_pid':123,'process_identity':{'birth':'old'}}
    newer={**payload,'runner_status':'completed','marker':'preserve newer writer'}
    database.put_simulation_run(payload)
    monkeypatch.setattr('os.kill',lambda *args:None)
    def replaced(pid):database.put_simulation_run(newer);return {'birth':'different'}
    monkeypatch.setattr('app.utils.process_identity.process_identity',replaced)
    try:
        result=SimulationRunner.reconcile_persisted_runs()
        assert result['interrupted']==0 and result['unknown']==1
        assert database.get_simulation_run('sim_race')==newer
    finally:_reset_runner()
