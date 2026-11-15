"""Small API and configuration defects found in the 2026-11-14 project review."""
import pytest
from flask import Flask

from app.api import graph_bp, market_bp
import app.api.graph  # noqa: F401  registers the routes
import app.api.market  # noqa: F401
from app.models.task import TaskManager
from app.services.simulation_config_generator import SimulationConfigGenerator
from app.services.task_execution import TaskRuntime
from app.utils import market_data


def test_market_error_never_returns_the_provider_url_or_key(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(market_bp, url_prefix='/api/market')
    monkeypatch.setattr(market_data, 'is_enabled', lambda: True)

    def fail(*args, **kwargs):
        raise RuntimeError('404 for url: https://provider.test/obs?series_id=BOGUS&api_key=SECRET-KEY')
    monkeypatch.setattr(market_data, 'resolve_target', fail)

    body = app.test_client().get('/api/market/resolve?kind=indicator&symbol=BOGUS').get_data(as_text=True)

    assert 'SECRET-KEY' not in body and 'provider.test' not in body
    assert 'Market data lookup failed' in body


def test_market_error_keeps_the_safe_application_message(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(market_bp, url_prefix='/api/market')
    monkeypatch.setattr(market_data, 'is_enabled', lambda: True)

    def fail(*args, **kwargs):
        raise market_data.MarketDataError('FRED_API_KEY not set; cannot fetch macro indicator')
    monkeypatch.setattr(market_data, 'resolve_target', fail)

    payload = app.test_client().get('/api/market/resolve?kind=indicator&symbol=GDP').get_json()

    assert payload == {'success': False, 'error': 'FRED_API_KEY not set; cannot fetch macro indicator'}


def test_task_list_route_returns_tasks(monkeypatch):
    monkeypatch.setattr(TaskManager, '_repository', None)
    monkeypatch.setattr(TaskManager, '_runtime', TaskRuntime(None))
    monkeypatch.setattr(TaskManager, '_instance', None)
    task_id = TaskManager().create_task('synthetic')
    app = Flask(__name__)
    app.register_blueprint(graph_bp, url_prefix='/api/graph')

    response = app.test_client().get('/api/graph/tasks')

    assert response.status_code == 200
    assert [task['task_id'] for task in response.get_json()['data']] == [task_id]


@pytest.mark.parametrize('bad', [0, -5, '60', 'soon', None, 10**9, 1.5, float('inf'), float('nan')])
def test_time_config_from_the_model_is_made_usable(bad):
    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)

    config = generator._parse_time_config({'minutes_per_round': bad, 'total_simulation_hours': bad}, num_entities=20)

    assert isinstance(config.minutes_per_round, int) and 0 < config.minutes_per_round <= 24 * 60
    assert isinstance(config.total_simulation_hours, int) and 0 < config.total_simulation_hours <= 24 * 365
