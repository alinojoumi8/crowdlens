"""Old preparation artifacts cannot override durable attempt ownership."""
import json
from types import SimpleNamespace

import pytest
from flask import Flask

from app.api import simulation, simulation_bp
from app.models.task import TaskManager
from app.services.task_execution import TaskRuntime
from app.storage.control_db import ControlDatabase


@pytest.fixture
def preparation(tmp_path, monkeypatch):
    root = tmp_path / 'simulations'
    folder = root / 'sim_retry'
    folder.mkdir(parents=True)
    state = {'simulation_id': 'sim_retry', 'project_id': 'proj_synthetic',
             'graph_id': 'graph_synthetic', 'status': 'preparing',
             'config_generated': True, 'profiles_count': 1,
             'enable_reddit': True, 'enable_twitter': True}
    (folder / 'state.json').write_text(json.dumps(state))
    (folder / 'simulation_config.json').write_text('{}')
    (folder / 'reddit_profiles.json').write_text('[{}]')
    (folder / 'twitter_profiles.csv').write_text('user_id,name\n0,Synthetic\n')
    db = ControlDatabase(tmp_path / 'control.db')
    clock = [100.0]
    runtime = TaskRuntime(db, clock=lambda: clock[0])
    monkeypatch.setattr(TaskManager, '_repository', db)
    monkeypatch.setattr(TaskManager, '_runtime', runtime)
    monkeypatch.setattr(TaskManager, '_instance', None)
    monkeypatch.setattr(simulation.Config, 'OASIS_SIMULATION_DATA_DIR', str(root))
    monkeypatch.setattr(simulation.SimulationManager, 'SIMULATION_DATA_DIR', str(root))
    attempt = runtime.admit({'task_id': 'prepare_retry', 'task_type': 'simulation_prepare',
                            'status': 'processing', 'created_at': '2026-10-02T00:00:00',
                            'updated_at': '2026-10-02T00:00:00',
                            'metadata': {'simulation_id': 'sim_retry'}},
                           [{'key': 'simulation:sim_retry', 'root': str(root)}])
    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.extensions['neo4j_storage'] = object()
    dispatched = []
    monkeypatch.setattr(TaskManager, 'start_task', lambda self, identifier, *a, **kw: dispatched.append(identifier))
    monkeypatch.setattr(simulation.ProjectManager, 'get_project', lambda _: SimpleNamespace(
        project_id='proj_synthetic', simulation_requirement='Synthetic preparation recovery.', prediction_settings={}))
    monkeypatch.setattr(simulation.ProjectManager, 'get_extracted_text', lambda _: 'Synthetic parcel text.')
    monkeypatch.setattr(simulation, 'EntityReader', lambda _: SimpleNamespace(
        filter_defined_entities=lambda **kw: SimpleNamespace(filtered_count=1, entity_types=['Person'])))
    yield app.test_client(), runtime, clock, folder, dispatched, attempt
    runtime.close()


@pytest.mark.parametrize('with_task_id', [False, True])
@pytest.mark.parametrize('expired', [False, True])
def test_preparation_poll_preserves_active_or_failed_attempt(preparation, with_task_id, expired):
    client, runtime, clock, folder, _, _ = preparation
    if expired:
        clock[0] = 131.0
        runtime.reconcile()
    before = (folder / 'state.json').read_bytes()
    body = {'simulation_id': 'sim_retry'}
    if with_task_id:
        body['task_id'] = 'prepare_retry'
    response = client.post('/api/simulation/prepare/status', json=body)
    assert response.status_code == 200
    data = response.json['data']
    assert data['status'] == ('failed' if expired else 'processing')
    assert data['already_prepared'] is False
    assert data['task_id'] == 'prepare_retry'
    if expired:
        assert data['error'] == 'ownership_lease_expired'
    assert (folder / 'state.json').read_bytes() == before


def test_manual_prepare_after_expiry_admits_new_attempt_without_force(preparation):
    client, runtime, clock, folder, dispatched, _ = preparation
    clock[0] = 131.0
    runtime.reconcile()
    response = client.post('/api/simulation/prepare', json={'simulation_id': 'sim_retry'})
    assert response.status_code == 200
    assert response.json['data']['already_prepared'] is False
    identifier = response.json['data']['task_id']
    assert identifier != 'prepare_retry'
    assert dispatched == [identifier]
    assert runtime.binding('simulation:sim_retry')['task_id'] == identifier
    assert json.loads((folder / 'state.json').read_text())['status'] == 'preparing'


def test_active_prepare_cannot_be_reused_as_ready_or_replaced(preparation):
    client, _, _, folder, dispatched, _ = preparation
    before = (folder / 'state.json').read_bytes()
    response = client.post('/api/simulation/prepare', json={'simulation_id': 'sim_retry'})
    assert response.status_code == 409
    assert response.json['error'] == 'resource_has_active_task'
    assert dispatched == []
    assert (folder / 'state.json').read_bytes() == before


def test_completed_preparation_remains_reusable(preparation):
    client, runtime, _, folder, dispatched, attempt = preparation
    state = json.loads((folder / 'state.json').read_text())
    state['status'] = 'ready'
    (folder / 'state.json').write_text(json.dumps(state))
    runtime.update(attempt, {'status': 'completed'})
    response = client.post('/api/simulation/prepare/status', json={'simulation_id': 'sim_retry'})
    assert response.status_code == 200
    assert response.json['data']['status'] == 'ready'
    assert response.json['data']['already_prepared'] is True
    assert not dispatched


@pytest.mark.parametrize('override, expected', [(None, 6), (3, 3)])
def test_regeneration_preserves_saved_agent_cap_over_project_defaults(preparation, monkeypatch, override, expected):
    client, runtime, clock, folder, _, _ = preparation
    state = json.loads((folder / 'state.json').read_text())
    state['prediction_settings'] = {'agent_count': 6, 'ensemble_runs': 1}
    state['forecast_mode'] = 'legal_case'
    state['forecast_horizon'] = 'Next procedural decision'
    (folder / 'state.json').write_text(json.dumps(state))
    monkeypatch.setattr(simulation.ProjectManager, 'get_project', lambda _: SimpleNamespace(
        project_id='proj_synthetic', simulation_requirement='Synthetic preparation recovery.',
        prediction_settings={'agent_count': 48}))
    entities = [SimpleNamespace(get_entity_type=lambda: 'Person') for _ in range(40)]
    monkeypatch.setattr(simulation, 'EntityReader', lambda _: SimpleNamespace(
        filter_defined_entities=lambda **kw: SimpleNamespace(filtered_count=40, entity_types=['Person'], entities=entities)))
    clock[0] = 131.0
    runtime.reconcile()
    body = {'simulation_id': 'sim_retry'}
    if override is not None:
        body['prediction_settings'] = {'agent_count': override}
    response = client.post('/api/simulation/prepare', json=body)
    assert response.status_code == 200
    assert response.json['data']['expected_entities_count'] == expected
    assert response.json['data']['prediction_settings']['agent_count'] == expected
    assert response.json['data']['forecast_settings']['ensemble_runs'] == 1
    assert response.json['data']['forecast_settings']['forecast_mode'] == 'legal_case'
    assert response.json['data']['forecast_settings']['forecast_horizon'] == 'Next procedural decision'


@pytest.mark.parametrize('settings,graph_failure,expected', [
    ({'participant_ids': ['missing']}, False, 400),
    ({'participant_ids': ['leo'], 'entity_types_exclude': ['Owner']}, False, 400),
    ({'participant_ids': ['leo', 'maya'], 'agent_count': 1}, False, 400),
    ({'participant_ids': ['leo']}, True, 503),
])
def test_explicit_roster_rejected_before_dispatch(preparation, monkeypatch, settings, graph_failure, expected):
    client, runtime, clock, folder, dispatched, _ = preparation
    clock[0] = 131.0
    runtime.reconcile()
    before = (folder / 'state.json').read_bytes()
    def read(**kwargs):
        if graph_failure:
            raise RuntimeError('graph offline')
        return SimpleNamespace(filtered_count=2, entity_types=['Owner','Person'], entities=[
            SimpleNamespace(uuid='leo', name='Leo', get_entity_type=lambda:'Owner'),
            SimpleNamespace(uuid='maya', name='Maya', get_entity_type=lambda:'Person')])
    monkeypatch.setattr(simulation, 'EntityReader', lambda _: SimpleNamespace(filter_defined_entities=read))
    response = client.post('/api/simulation/prepare', json={'simulation_id':'sim_retry','prediction_settings':settings})
    assert response.status_code == expected, response.json
    assert not dispatched
    assert (folder / 'state.json').read_bytes() == before


def test_reusing_prepared_simulation_cannot_silently_ignore_new_roster(preparation):
    client, runtime, _, folder, dispatched, attempt = preparation
    state = json.loads((folder/'state.json').read_text())
    state['status'] = 'ready'
    (folder/'state.json').write_text(json.dumps(state))
    runtime.update(attempt, {'status': 'completed'})
    before = (folder/'state.json').read_bytes()
    response = client.post('/api/simulation/prepare', json={'simulation_id':'sim_retry',
        'prediction_settings':{'participant_ids':['leo']}})
    assert response.status_code == 409, response.json
    assert 'differs' in response.json['error']
    assert dispatched == []
    assert (folder/'state.json').read_bytes() == before


def test_prepared_activation_mode_change_requires_explicit_regeneration(preparation):
    client, runtime, _, folder, dispatched, attempt = preparation
    state = json.loads((folder/'state.json').read_text()); state['status'] = 'ready'
    (folder/'state.json').write_text(json.dumps(state)); runtime.update(attempt, {'status':'completed'})
    before = (folder/'state.json').read_bytes()
    response = client.post('/api/simulation/prepare', json={'simulation_id':'sim_retry',
        'prediction_settings':{'activation_mode':'smoke_round_robin'}})
    assert response.status_code == 409
    assert not dispatched and (folder/'state.json').read_bytes() == before
