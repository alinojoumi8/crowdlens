"""Destructive ensemble operations must still own the current attempt."""
import json

import pytest

from app.models.task import TaskManager
from app.services.ensemble_runner import EnsembleRunner
from app.services.simulation_runner import SimulationRunner
from app.services.task_execution import OwnershipLost, TaskRuntime
from app.storage.control_db import ControlDatabase


@pytest.fixture
def ensemble_owner(tmp_path, monkeypatch):
    db = ControlDatabase(tmp_path / 'control.db')
    clock = [100.0]
    runtime = TaskRuntime(db, clock=lambda: clock[0])
    monkeypatch.setattr(TaskManager, '_repository', db)
    monkeypatch.setattr(TaskManager, '_runtime', runtime)
    monkeypatch.setattr(SimulationRunner, '_repository', db)
    monkeypatch.setattr(SimulationRunner, '_run_states', {})
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    monkeypatch.setattr(SimulationRunner, 'get_run_state', lambda *_: None)
    monkeypatch.setattr(SimulationRunner, 'close_simulation_env', lambda *a, **kw: None)
    folder = tmp_path / 'sim_synthetic'
    folder.mkdir()
    resource = [{'key': 'ensemble:sim_synthetic', 'root': str(tmp_path)}]

    def admit(identifier):
        return runtime.admit({'task_id': identifier, 'task_type': 'simulation_ensemble',
                              'status': 'processing'}, resource)

    old = admit('old')

    def replace():
        clock[0] = 131.0
        runtime.reconcile()
        new = admit('new')
        state = {'simulation_id': 'sim_synthetic', 'runner_status': 'running', 'marker': 'new_owner'}
        db.put_simulation_run(state)
        (folder / 'run_state.json').write_text(json.dumps(state))
        return new

    yield runtime, db, folder, old, replace
    runtime.close()


def test_replacement_during_shutdown_cannot_be_deleted_by_old_reset(ensemble_owner, monkeypatch):
    runtime, db, folder, old, replace = ensemble_owner
    monkeypatch.setattr(SimulationRunner, 'close_simulation_env', lambda *a, **kw: replace())
    with old.bind(), pytest.raises(OwnershipLost):
        EnsembleRunner._reset('sim_synthetic')
    assert json.loads((folder / 'run_state.json').read_text())['marker'] == 'new_owner'
    assert db.get_simulation_run('sim_synthetic')['marker'] == 'new_owner'
    assert runtime.get('new')['status'] == 'processing'


def test_replacement_after_reset_cannot_dispatch_old_sample(ensemble_owner, monkeypatch):
    _, _, _, old, replace = ensemble_owner
    dispatched = []
    monkeypatch.setattr(EnsembleRunner, '_load_config', lambda _: {'simulation_requirement': 'Synthetic scenario'})
    monkeypatch.setattr(EnsembleRunner, '_reset', lambda _: replace())
    monkeypatch.setattr(EnsembleRunner, '_wait_for_completion', lambda *a: False)
    monkeypatch.setattr(SimulationRunner, 'start_simulation', lambda **kw: dispatched.append(kw))
    with old.bind(), pytest.raises(OwnershipLost):
        EnsembleRunner.run_ensemble('sim_synthetic', runs=1)
    assert not dispatched


def test_late_shutdown_cannot_close_replacement_environment(ensemble_owner, monkeypatch):
    _, _, _, old, replace = ensemble_owner
    replace()
    closed = []
    monkeypatch.setattr(SimulationRunner, 'close_simulation_env', lambda *a, **kw: closed.append(a))
    with old.bind(), pytest.raises(OwnershipLost):
        EnsembleRunner._shutdown('sim_synthetic')
    assert not closed


def test_valid_owner_can_cleanup_its_previous_sample(ensemble_owner):
    _, db, folder, old, _ = ensemble_owner
    (folder / 'run_state.json').write_text('{}')
    (folder / 'simulation_config.json').write_text('{"keep": true}')
    db.put_simulation_run({'simulation_id': 'sim_synthetic', 'runner_status': 'stopped'})
    with old.bind():
        EnsembleRunner._reset('sim_synthetic')
    assert not (folder / 'run_state.json').exists()
    assert db.get_simulation_run('sim_synthetic') is None
    assert json.loads((folder / 'simulation_config.json').read_text()) == {'keep': True}
