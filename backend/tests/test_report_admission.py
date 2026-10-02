"""Root retries retain their task identity across completion, failure and restart."""
import pytest

from test_evidence_quality_faults import ROOT_REQUEST, root_admission
from app.models.task import TaskManager, TaskStatus
from app.services.task_execution import TaskRuntime
from app.storage.control_db import ControlDatabase


def test_same_key_with_changed_input_is_a_conflict(root_admission):
    app, db, dispatched = root_admission
    with app.test_client() as client:
        first = client.post('/api/report/generate', json=ROOT_REQUEST)
        changed = client.post('/api/report/generate', json={**ROOT_REQUEST, 'report_depth': 'deep'})
    assert first.status_code == 200
    assert changed.status_code == 409
    assert changed.json['error'] == 'request_key_conflict'
    assert len(db.list_tasks()) == len(dispatched) == 1


@pytest.mark.parametrize('request_key', ['', 'bad/key', 1, 'x'*129])
def test_invalid_key_cannot_start_work(root_admission, request_key):
    app, db, dispatched = root_admission
    response = app.test_client().post('/api/report/generate', json={**ROOT_REQUEST, 'request_key': request_key})
    assert response.status_code == 400
    assert not db.list_tasks() and not dispatched


def test_distinct_request_keys_cannot_run_same_simulation_concurrently(root_admission):
    app, db, dispatched = root_admission
    client = app.test_client()
    first = client.post('/api/report/generate', json=ROOT_REQUEST)
    other = client.post('/api/report/generate', json={**ROOT_REQUEST, 'request_key': 'different', 'force_regenerate': True})
    assert first.status_code == 200
    assert other.status_code == 409
    assert len(db.list_tasks()) == len(dispatched) == 1


@pytest.mark.parametrize('status', [TaskStatus.COMPLETED, TaskStatus.FAILED])
def test_terminal_request_replay_does_not_dispatch_even_after_new_runtime(root_admission, monkeypatch, status):
    app, db, dispatched = root_admission
    client = app.test_client()
    request = {**ROOT_REQUEST, 'force_regenerate': True}
    first = client.post('/api/report/generate', json=request).json['data']
    TaskManager().update_task(first['task_id'], status=status,
        result={'status': 'needs_review'} if status == TaskStatus.COMPLETED else None,
        error='synthetic_failure' if status == TaskStatus.FAILED else None)
    new_runtime = TaskRuntime(ControlDatabase(db.path))
    monkeypatch.setattr(TaskManager, '_runtime', new_runtime)
    try:
        replay = client.post('/api/report/generate', json=request)
        assert replay.status_code == 200
        assert replay.json['data']['task_id'] == first['task_id']
        assert replay.json['data']['report_id'] == first['report_id']
        assert replay.json['data']['status'] == ('needs_review' if status == TaskStatus.COMPLETED else 'failed')
        assert len(db.list_tasks()) == len(dispatched) == 1
    finally:
        new_runtime.close()


def test_manual_retry_after_expiry_requires_new_key(root_admission):
    app, db, dispatched = root_admission
    client = app.test_client()
    first = client.post('/api/report/generate', json=ROOT_REQUEST).json['data']
    runtime = TaskManager().runtime
    clock = runtime.clock
    now = clock()
    runtime.clock = lambda: now + 31
    try:
        replay = client.post('/api/report/generate', json=ROOT_REQUEST).json['data']
        assert replay['status'] == 'failed'
        assert replay['error'] == 'ownership_lease_expired'
        retry = client.post('/api/report/generate', json={**ROOT_REQUEST, 'request_key': 'manual-retry'}).json['data']
        assert retry['task_id'] != first['task_id']
        assert retry['report_id'] != first['report_id']
        assert len(db.list_tasks()) == len(dispatched) == 2
    finally:
        runtime.clock = clock
