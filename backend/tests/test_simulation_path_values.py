"""simulation_id and platform become file path parts, so the API refuses path syntax."""
import pytest
from flask import Flask

from app.api import simulation_bp
import app.api.simulation  # noqa: F401  registers the routes


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.config import Config
    from app.services.simulation_manager import SimulationManager
    root = tmp_path / 'root' / 'uploads' / 'simulations'
    root.mkdir(parents=True)
    monkeypatch.setattr(Config, 'OASIS_SIMULATION_DATA_DIR', str(root))
    monkeypatch.setattr(SimulationManager, 'SIMULATION_DATA_DIR', str(root))
    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    return app.test_client()


@pytest.mark.parametrize('path', [
    '/api/simulation/sim_a/posts?platform=../sim_b/reddit',
    '/api/simulation/sim_a/profiles?platform=../sim_b/reddit',
    '/api/simulation/sim_a/profiles/realtime?platform=/etc/passwd',
    '/api/simulation/sim_a/posts?platform=..%5Csim_b%5Creddit',
])
def test_platform_cannot_carry_a_path(client, path):
    response = client.get(path)

    assert response.status_code == 400
    assert response.get_json() == {'success': False, 'error': 'Invalid platform'}


@pytest.mark.parametrize('simulation_id', ['../../../../tmp/x', '..', 'a/b', 'a\\b', 'a\x00b'])
def test_simulation_id_cannot_carry_a_path(client, simulation_id, tmp_path):
    response = client.post('/api/simulation/prepare', json={'simulation_id': simulation_id})

    assert response.status_code == 400
    assert response.get_json() == {'success': False, 'error': 'Invalid simulation id'}
    assert sorted(path.name for path in tmp_path.rglob('*')) == ['root', 'simulations', 'uploads']


def test_normal_values_still_reach_the_route(client):
    response = client.get('/api/simulation/sim_missing_for_test/posts?platform=twitter')

    assert response.get_json().get('error') != 'Invalid platform'
