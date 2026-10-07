"""Frozen pre-fix fault contracts: real Flask/SQLite admission, no generation."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
from types import SimpleNamespace

from flask import Flask
import pytest
import requests


@pytest.fixture
def root_admission(tmp_path, monkeypatch):
    from app.api import report, report_bp
    from app.models.task import TaskManager
    from app.services.task_execution import TaskRuntime
    from app.storage.control_db import ControlDatabase

    db = ControlDatabase(tmp_path / 'root-admission.db')
    runtime = TaskRuntime(db)
    monkeypatch.setattr(TaskManager, '_repository', db)
    monkeypatch.setattr(TaskManager, '_runtime', runtime)
    monkeypatch.setattr(report.ReportManager, 'REPORTS_DIR', str(tmp_path / 'reports'))
    monkeypatch.setattr(report.ProjectManager, 'get_project', lambda _: SimpleNamespace(
        project_id='eq_project', graph_id='eq_graph', simulation_requirement='Synthetic parcel record.'))
    monkeypatch.setattr(report.SimulationManager, 'get_simulation', lambda *_: SimpleNamespace(
        project_id='eq_project', graph_id='eq_graph'))
    monkeypatch.setattr(report, 'load_simulation_config', lambda _: {})
    monkeypatch.setattr(report, 'GraphToolsService', lambda **kw: object())
    dispatched = []
    monkeypatch.setattr(TaskManager, 'start_task', lambda self, identifier, *a, **kw: dispatched.append(identifier))
    app = Flask(__name__)
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.extensions['neo4j_storage'] = SimpleNamespace(get_embedding_status=lambda _: {'safe_to_report': True})
    yield app, db, dispatched
    runtime.close()


ROOT_REQUEST = {'simulation_id': 'eq_sim', 'report_mode': 'legal_case',
                'request_key': 'eq_response_loss_v1'}


def assert_single_admission(responses, db, dispatched, record_property):
    statuses = [response.status_code for response in responses]
    accepted = [response.json['data'] for response in responses if response.status_code in {200, 202}]
    observation = {'statuses': statuses, 'task_ids': [row['task_id'] for row in accepted],
                   'report_ids': [row['report_id'] for row in accepted],
                   'persisted_tasks': len(db.list_tasks()), 'dispatches': len(dispatched),
                   'real_model_calls': 0, 'generation_executed': False}
    record_property('fault_observation', json.dumps(observation, sort_keys=True))
    assert all(status in {200, 202, 409} for status in statuses), observation
    assert accepted, observation
    assert len(db.list_tasks()) == 1, observation
    assert len(dispatched) == 1, observation
    assert len({row['task_id'] for row in accepted}) == 1, observation
    assert len({row['report_id'] for row in accepted}) == 1, observation


def test_lost_root_response_retry_does_not_dispatch_twice(root_admission, record_property):
    app, db, dispatched = root_admission
    client = app.test_client()
    # The first response is received only by the test observer, lost to the caller.
    first = client.post('/api/report/generate', json=ROOT_REQUEST)
    retry = client.post('/api/report/generate', json=ROOT_REQUEST)
    assert_single_admission([first, retry], db, dispatched, record_property)


def test_concurrent_root_requests_admit_one_attempt(root_admission, record_property):
    app, db, dispatched = root_admission
    barrier = Barrier(2)
    def submit(_):
        with app.test_client() as client:
            barrier.wait(timeout=5)
            return client.post('/api/report/generate', json=ROOT_REQUEST)
    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(submit, range(2)))
    assert_single_admission(responses, db, dispatched, record_property)


def test_anthropic_retry_budget_observation_is_per_attempt(monkeypatch, record_property):
    """Characterize an existing bound; do not invent an aggregate deadline contract."""
    from app.utils.llm_client import LLMClient
    from app.utils import llm_client
    elapsed, timeouts, sleeps = [0.0], [], []
    def timeout(*args, **kwargs):
        timeouts.append(kwargs['timeout'])
        elapsed[0] += kwargs['timeout']
        raise requests.exceptions.Timeout('synthetic full transport timeout')
    def sleep(seconds):
        sleeps.append(seconds)
        elapsed[0] += seconds
    monkeypatch.setattr(llm_client.requests, 'post', timeout)
    monkeypatch.setattr(llm_client.time, 'sleep', sleep)
    monkeypatch.setenv('LLM_HTTP_MAX_RETRIES', '4')
    monkeypatch.setenv('LLM_HTTP_RETRY_BASE_SECONDS', '2')
    monkeypatch.setenv('LLM_HTTP_RETRY_MAX_SECONDS', '30')
    client = LLMClient.__new__(LLMClient)
    client.timeout = 300.0
    client.model = 'synthetic'
    client.base_url = 'https://synthetic.invalid'
    with pytest.raises(requests.exceptions.Timeout):
        client._post_anthropic_with_retry('https://synthetic.invalid/v1/messages', {}, {})
    observation = {'transport_attempts': len(timeouts), 'timeout_each_seconds': timeouts,
                   'backoff_seconds': sleeps, 'simulated_elapsed_seconds': elapsed[0],
                   'real_elapsed_seconds': None, 'real_model_calls': 0,
                   'aggregate_deadline_enforced': False}
    record_property('fault_observation', json.dumps(observation, sort_keys=True))
    assert timeouts == [300.0] * 5
    assert sleeps == [2.0, 4.0, 8.0, 16.0]
    assert elapsed[0] == 1530.0
