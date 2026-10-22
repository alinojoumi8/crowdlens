"""Shared admission limits; synthetic identities and transports only."""
import concurrent.futures
import multiprocessing
import os
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import pytest
from flask import Flask

from app.api.execution import install_workflow_controls
from app.authentication import install_authentication
from app.config import Config
from app.storage.control_db import ControlDatabase
from app.models.task import TaskManager
from app.services.task_execution import TaskRuntime
from app.services import workspace as w, administrator_quotas as quotas
from app.services.workflow_execution import WorkflowLedger, WorkflowHalt, execution_scope, transport_attempt
from test_authentication import login


@pytest.fixture
def quota_app(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='x' * 40, AUTH_MODE='oidc',
        AUTH_ALLOW_HTTP_LOOPBACK=True, AUTH_BASE_URL='http://localhost',
        AUTH_ISSUER='http://localhost:9999', AUTH_CLIENT_ID='fixture', AUTH_CLIENT_SECRET='fixture',
        AUTH_ADMIN_EMAIL='admin@example.test', AUTH_DB_PATH=str(tmp_path / 'auth.db'))
    for key, value in dict(LLM_DEFAULT_PROVIDER='synthetic', LLM_MODEL_NAME='synthetic',
            LLM_BASE_URL='http://127.0.0.1:1/anthropic', EMBEDDING_PROVIDER='ollama',
            EMBEDDING_BASE_URL='http://127.0.0.1:11434').items():
        monkeypatch.setattr(Config, key, value)
    app.extensions['control_db'] = ControlDatabase(tmp_path / 'control.db')
    runtime = TaskRuntime(app.extensions['control_db'])
    monkeypatch.setattr(TaskManager, '_repository', app.extensions['control_db'])
    monkeypatch.setattr(TaskManager, '_runtime', runtime)
    monkeypatch.setattr(TaskManager, '_instance', None)
    install_authentication(app)
    app.add_url_rule('/api/work', 'work', lambda: {'success': True}, methods=['GET', 'POST'])
    def generate():
        from flask import request
        for _ in range(request.json.get('calls', 1)):
            with transport_attempt('synthetic', Config.LLM_BASE_URL) as receipt:
                receipt['usage'] = dict(input_tokens=1, output_tokens=0)
        return {'success': True}
    app.add_url_rule('/api/report/generate', 'report.generate_report', generate, methods=['POST'])
    app.add_url_rule('/api/start-task', 'start_task',
        lambda: {'task_id': TaskManager().create_task('synthetic')}, methods=['POST'])
    for path, endpoint, methods in [
        ('/api/poll/proposal', 'report.get_evidence_proposal', ['GET']),
        ('/api/poll/run', 'simulation.get_run_status', ['GET']),
        ('/api/poll/prepare', 'simulation.get_prepare_status', ['POST']),
        ('/api/poll/ensemble', 'simulation.get_ensemble_status', ['POST']),
    ]:
        app.add_url_rule(path, endpoint, lambda: {'success': True}, methods=methods)
    install_workflow_controls(app)
    client = app.test_client()
    user, csrf = login(app, client)
    yield app, client, user, {'X-CrowdLens-CSRF': csrf}
    runtime.close()


def authorization(key='first'):
    return dict(provider='synthetic', model='synthetic', request_key=key,
        input_description='fictional quota fixture', max_requests=100, max_seconds=60, confirmed=True)


def test_oidc_authorization_requires_administrator_quota(quota_app):
    app, client, user, headers = quota_app
    response = client.post('/api/execution/authorize', json=authorization(), headers=headers)
    assert response.status_code == 429
    assert response.json['error'] == 'quota_not_configured'
    assert response.json['recovery_requires_action'] is True


def policy(*, global_scope=False, **overrides):
    limits = dict(requests=100, daily_requests=100, estimated_micro_usd=10_000_000,
        daily_estimated_micro_usd=10_000_000, operations=1000, daily_operations=1000,
        storage_write_bytes=1_000_000, active_work=10)
    limits.update(overrides)
    value = dict(admission_open=True, limits=limits)
    if global_scope:
        value['pricing'] = dict(currency='USD', reserve_usd='0.05', input_usd_per_million='1',
            output_usd_per_million='10', price_reference='Fictional quota rates v1, not provider prices')
    return value


def configure(app, client, user, headers, *, shared=None, individual=None):
    for scope, value in [('global', shared or policy(global_scope=True)),
                         (user['id'], individual or policy())]:
        r = client.put('/api/execution/quotas/' + scope, json=value, headers=headers)
        assert r.status_code == 200, r.json
    return app.extensions['workflow_ledger']


def new_workflow(ledger, key='first'):
    return ledger.authorize(**{**authorization(key), 'base_url': Config.LLM_BASE_URL})['workflow_id']


def physical(ledger, wid, epoch=1):
    return ledger.admit(wid, epoch, 'fixture', 'synthetic', 'http://127.0.0.1:1/anthropic')


def process_physical(args):
    path, auth_path, owner, wid = args
    w.configure(auth_path)
    try:
        with w.workspace_scope(owner):
            return physical(WorkflowLedger(path), wid)
    except WorkflowHalt as exc:
        return exc.reason
    finally:
        w.configure()


def process_task(args):
    path, auth_path, owner, number = args
    w.configure(auth_path)
    try:
        runtime = TaskRuntime(ControlDatabase(path))
        with w.workspace_scope(owner):
            runtime.admit(dict(task_id=f'quota_task_{number}', task_type='fixture', status='pending',
                created_at='2026-10-21T00:00:00+00:00', updated_at='2026-10-21T00:00:00+00:00'))
        return True
    except WorkflowHalt as exc:
        return exc.reason
    finally:
        w.configure()


def process_renewal_race(args):
    path, auth_path, owner, wid, action, number = args
    w.configure(auth_path)
    try:
        with w.workspace_scope(owner):
            ledger = WorkflowLedger(path)
            if action == 'renew':
                ledger.reauthorize(wid, max_requests=101, max_seconds=60, confirmed=True,
                    acknowledge_unknown=True, request_key=f'concurrent-renew-{number}', budget_usd='10')
                return 'renewed'
            return physical(ledger, wid, ledger.status(wid)['epoch'])
    except WorkflowHalt as exc:
        return exc.reason
    finally:
        w.configure()


def test_only_administrator_can_change_quotas_and_csrf_is_required(quota_app):
    app, client, user, headers = quota_app
    url = '/api/execution/quotas/global'
    assert app.test_client().put(url, json=policy(global_scope=True)).status_code == 401
    assert client.put(url, json=policy(global_scope=True)).status_code == 403
    invite = app.extensions['auth_store'].invite('tester@example.test', user['id'])
    tester = app.test_client()
    _, csrf = login(app, tester, 'tester@example.test', 'tester', invite)
    assert tester.put(url, json=policy(global_scope=True), headers={'X-CrowdLens-CSRF': csrf}).status_code == 403
    configure(app, client, user, headers)
    assert client.get(url).json['data']['provider_identity']['model'] == 'synthetic'
    with app.extensions['workflow_ledger'].transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM quota_audit').fetchone()[0] == 2


@pytest.mark.parametrize('invalid', [-1, 1.5, True, None, '100', 10**13])
def test_invalid_limits_never_replace_a_policy(quota_app, invalid):
    app, client, user, headers = quota_app
    configure(app, client, user, headers)
    bad = policy(global_scope=True, requests=invalid)
    assert client.put('/api/execution/quotas/global', json=bad, headers=headers).status_code == 400
    assert client.get('/api/execution/quotas/global').json['data']['policy']['limits']['requests'] == 100


def test_client_cannot_change_shared_prices_or_reservations(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    spoof = {**authorization(), 'spend': dict(currency='USD', budget_usd='1', reserve_usd='0.000001',
        input_usd_per_million='0', output_usd_per_million='0', price_reference='client spoof')}
    r = client.post('/api/execution/authorize', json=spoof, headers=headers)
    assert r.status_code == 201
    spend = r.json['data']['spend']
    assert spend['reserve_micro_usd'] == 50_000
    assert spend['input_rate_micro_usd'] == 1_000_000
    assert 'Fictional quota' in spend['price_reference']
    with w.workspace_scope(user['id']):
        ticket = physical(ledger, r.json['data']['workflow_id'])
        with ledger.transaction() as db:
            assert quotas.usage(db, 'global', time.time())['reserved_micro_usd'] == 50_000
        ledger.finish(ticket, status='response', usage=dict(input_tokens=1, output_tokens=1))


def test_shared_requests_are_atomic_across_users_workflows_and_processes(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, shared=policy(global_scope=True, requests=3), individual=policy(requests=2))
    owners = [user['id'], 'second-fixture-owner']
    jobs = []
    with ledger.transaction() as db:
        quotas.update_policy(db, owners[1], policy(requests=2), user['id'], time.time())
    for owner in owners:
        with w.workspace_scope(owner):
            for number in range(6):
                wid = new_workflow(ledger, str(number))
                jobs.append((ledger.path, app.config['AUTH_DB_PATH'], owner, wid))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn')) as pool:
        results = list(pool.map(process_physical, jobs))
    assert sum(isinstance(r, dict) for r in results) == 3
    assert {r for r in results if isinstance(r, str)} == {'quota_requests_limit'}
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['requests'] == 3
        assert all(quotas.usage(db, owner, time.time())['requests'] <= 2 for owner in owners)
        assert sum(__import__('json').loads(row[0])['admitted'] for row in db.execute('SELECT payload FROM workflows')) == 3


def test_new_authorizations_renewals_and_restart_never_reset_shared_usage(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(requests=1))
    with w.workspace_scope(user['id']):
        wid = new_workflow(ledger)
        ticket = physical(ledger, wid)
        ledger.finish(ticket, status='response', usage=dict(input_tokens=0, output_tokens=0))
        ledger.stop(wid)
        renewed = ledger.reauthorize(wid, max_requests=101, max_seconds=60, confirmed=True,
                                    request_key='renew', budget_usd='10')
        assert renewed['epoch'] == 2
        restarted = WorkflowLedger(ledger.path)
        fresh = new_workflow(restarted, 'fresh')
        for candidate, epoch in [(wid, 2), (fresh, 1)]:
            with pytest.raises(WorkflowHalt, match='quota_requests_limit'):
                physical(restarted, candidate, epoch)
        assert restarted.status(wid)['admitted'] == 1
        assert restarted.status(fresh)['admitted'] == 0


def test_concurrent_renewals_and_admissions_share_one_persistent_ceiling(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(requests=3))
    with w.workspace_scope(user['id']):
        wid = new_workflow(ledger)
    actions = ['admit'] * 8 + ['renew'] * 4 + ['admit'] * 8
    jobs = [(ledger.path, app.config['AUTH_DB_PATH'], user['id'], wid, action, i)
            for i, action in enumerate(actions)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn')) as pool:
        result = list(pool.map(process_renewal_race, jobs))
    accepted = sum(isinstance(r, dict) for r in result)
    assert accepted == 3
    assert result.count('renewed') == 4
    with WorkflowLedger(ledger.path).transaction() as db:
        used = quotas.usage(db, user['id'], time.time())
        assert used['requests'] == accepted
        assert used['reserved_micro_usd'] == accepted * 50_000


def test_unknown_reservations_survive_stop_renewal_restart_and_utc_day_rollover(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, shared=policy(global_scope=True,
        daily_requests=2, daily_estimated_micro_usd=100_000))
    now = [100_000.0]
    ledger.clock = lambda: now[0]
    with w.workspace_scope(user['id']):
        a, b = new_workflow(ledger, 'a'), new_workflow(ledger, 'b')
        ta, tb = physical(ledger, a), physical(ledger, b)
        ledger.finish(ta, status='delivery_or_usage_unknown')
        ledger.stop(a)
        ledger.reauthorize(a, max_requests=101, max_seconds=60, confirmed=True, request_key='renew', budget_usd='10')
        now[0] += 86400
        restarted = WorkflowLedger(ledger.path, clock=lambda: now[0])
        fresh = new_workflow(restarted, 'next-day')
        with pytest.raises(WorkflowHalt, match='quota_daily_estimated_micro_usd_limit'):
            physical(restarted, fresh)
        restarted.finish(tb, status='response', usage=dict(input_tokens=0, output_tokens=0))
        # Old, complete usage can settle after midnight; the unknown attempt stays reserved.
        physical(restarted, fresh)
        with restarted.transaction() as db:
            assert quotas.usage(db, 'global', now[0])['reserved_micro_usd'] == 100_000
            assert quotas.usage(db, 'global', now[0])['requests'] == 3


def test_estimate_overrun_closes_global_admission_and_settlement_is_idempotent(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    with w.workspace_scope(user['id']):
        wid = new_workflow(ledger)
        ticket = physical(ledger, wid)
        ledger.finish(ticket, status='response', usage=dict(input_tokens=100_000, output_tokens=0))
        ledger.finish(ticket, status='response', usage=dict(input_tokens=0, output_tokens=0))
        with ledger.transaction() as db:
            used = quotas.usage(db, 'global', time.time())
            assert used['estimated_micro_usd'] == 100_000
            assert used['reserved_micro_usd'] == 0
        with pytest.raises(WorkflowHalt, match='quota_admission_closed'):
            new_workflow(ledger, 'cannot-escape-overrun')


def test_global_kill_switch_blocks_existing_calls_but_preserves_stop_and_late_usage(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    with w.workspace_scope(user['id']):
        wid = new_workflow(ledger)
        ticket = physical(ledger, wid)
    closed = policy(global_scope=True); closed['admission_open'] = False
    assert client.put('/api/execution/quotas/global', json=closed, headers=headers).status_code == 200
    with w.workspace_scope(user['id']):
        with pytest.raises(WorkflowHalt, match='quota_admission_closed'):
            physical(WorkflowLedger(ledger.path), wid)
        ledger.finish(ticket, status='response', usage=dict(input_tokens=1, output_tokens=1))
        ledger.stop(wid)
        assert ledger.status(wid)['state'] == 'stopped'


def test_non_model_operations_are_shared_and_exhaustion_is_actionable(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(operations=1))
    assert client.post('/api/work', json={}, headers=headers).status_code == 200
    r = client.post('/api/work', json={}, headers=headers)
    assert r.status_code == 429
    assert r.json['error'] == 'quota_operations_limit'
    assert 'administrator' in r.json['next_action']
    with ledger.transaction() as db:
        assert quotas.usage(db, user['id'], time.time())['active_work'] == 0


def test_progress_polling_does_not_consume_or_require_operation_capacity(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(operations=0, active_work=0))
    from app.api import report_bp, simulation_bp
    actual = Flask('registered-poll-routes')
    actual.register_blueprint(report_bp)
    actual.register_blueprint(simulation_bp)
    for path, endpoint, method in [
        ('/api/poll/proposal', 'report.get_evidence_proposal', 'GET'),
        ('/api/poll/run', 'simulation.get_run_status', 'GET'),
        ('/api/poll/prepare', 'simulation.get_prepare_status', 'POST'),
        ('/api/poll/ensemble', 'simulation.get_ensemble_status', 'POST'),
    ]:
        assert endpoint in actual.view_functions
        for _ in range(3):
            assert client.open(path, method=method, json={} if method == 'POST' else None, headers=headers).status_code == 200
    assert client.get('/api/work').status_code == 429
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['operations'] == 0


def test_many_small_storage_writes_encode_only_incremental_input(quota_app, tmp_path, monkeypatch):
    from app.services import quota_io
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    encoded_characters = 0
    original = quota_io._Writer._encode
    def track(self, value):
        nonlocal encoded_characters
        encoded_characters += len(value)
        return original(self, value)
    monkeypatch.setattr(quota_io._Writer, '_encode', track)
    target = tmp_path / 'many-chunks.txt'
    with w.workspace_scope(user['id']), quota_io.open(target, 'w', encoding='utf-8') as stream:
        for _ in range(1000):
            stream.write('é\n')
        stream.flush()
        stream.write('end')
    assert target.read_text() == 'é\n' * 1000 + 'end'
    assert encoded_characters <= 2 * len(target.read_text())
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['storage_write_bytes'] == target.stat().st_size


@pytest.mark.parametrize('encoding', ['utf-16', 'iso2022_jp'])
def test_incremental_storage_encoding_counts_final_bytes_and_recovers_rejected_write(quota_app, tmp_path, encoding):
    from app.services.quota_io import open as quota_open
    app, client, user, headers = quota_app
    reference = tmp_path / 'reference.txt'
    with open(reference, 'w', encoding=encoding) as stream:
        stream.write('あ')
        stream.write('い')
    expected = reference.read_bytes()
    ledger = configure(app, client, user, headers, individual=policy(storage_write_bytes=len(expected)))
    target = tmp_path / 'encoded.txt'
    with w.workspace_scope(user['id']), quota_open(target, 'w', encoding=encoding) as stream:
        stream.write('あ')
        with pytest.raises(WorkflowHalt, match='quota_storage_write_bytes_limit'):
            stream.write('う' * 50)
        stream.write('い')
    assert target.read_bytes() == expected
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['storage_write_bytes'] == len(expected)


def test_empty_text_publication_cannot_skip_encoding_prefix_quota(quota_app, tmp_path):
    from app.services.quota_io import open as quota_open
    app, client, user, headers = quota_app
    configure(app, client, user, headers, individual=policy(storage_write_bytes=1))
    target = tmp_path / 'empty-utf16.txt'
    with w.workspace_scope(user['id']):
        with pytest.raises(WorkflowHalt, match='quota_storage_write_bytes_limit'):
            with quota_open(target, 'w', encoding='utf-16'):
                pass
    assert not target.exists()


def test_utc_operation_reset_retains_lifetime_usage(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(operations=2, daily_operations=1))
    now = [100_000.0]
    ledger.clock = lambda: now[0]
    assert client.post('/api/work', json={}, headers=headers).status_code == 200
    assert client.post('/api/work', json={}, headers=headers).json['error'] == 'quota_daily_operations_limit'
    now[0] += 86400
    assert client.post('/api/work', json={}, headers=headers).status_code == 200
    now[0] += 86400
    assert client.post('/api/work', json={}, headers=headers).json['error'] == 'quota_operations_limit'


def test_unfinished_http_slot_does_not_disappear_on_restart(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(active_work=1))
    with ledger.transaction() as db:
        quotas.begin_operation(db, user['id'], time.time())
    restarted = WorkflowLedger(ledger.path)
    with restarted.transaction() as db:
        with pytest.raises(WorkflowHalt, match='quota_active_work_limit'):
            quotas.begin_operation(db, user['id'], time.time())


def test_active_task_slot_survives_restart_and_releases_only_on_terminal_state(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(active_work=1))
    with w.workspace_scope(user['id']):
        task = TaskManager().create_task('synthetic')
        with WorkflowLedger(ledger.path).transaction() as db:
            assert quotas.usage(db, user['id'], time.time())['active_work'] == 1
        with pytest.raises(WorkflowHalt, match='quota_active_work_limit'):
            TaskManager().create_task('another')
        TaskManager().complete_task(task, {'fixture': True})
        assert TaskManager().create_task('after-completion')


def test_active_work_admission_is_serialized_across_processes_and_accounts(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, shared=policy(global_scope=True, active_work=2),
        individual=policy(active_work=1))
    second = 'second-fixture-owner'
    with ledger.transaction() as db:
        quotas.update_policy(db, second, policy(active_work=1), user['id'], time.time())
    jobs = [(ledger.path, app.config['AUTH_DB_PATH'], owner, i)
            for i, owner in enumerate([user['id']]*6 + [second]*6)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn')) as pool:
        results = list(pool.map(process_task, jobs))
    assert results.count(True) == 2
    assert {r for r in results if r is not True} == {'quota_active_work_limit'}
    with WorkflowLedger(ledger.path).transaction() as db:
        assert quotas.usage(db, 'global', time.time())['active_work'] == 2


def test_storage_write_budget_is_atomic_and_does_not_refund_overwrites_or_deletion(quota_app, tmp_path):
    from app.services.quota_io import open as quota_open
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(storage_write_bytes=8))
    target = tmp_path / 'artifact.txt'
    with w.workspace_scope(user['id']):
        with quota_open(target, 'w', encoding='utf-8') as stream:
            stream.write('éé')  # Four UTF-8 bytes.
        with quota_open(target, 'w', encoding='utf-8') as stream:
            stream.write('abcd')
        with pytest.raises(WorkflowHalt, match='quota_storage_write_bytes_limit'):
            with quota_open(target, 'w', encoding='utf-8') as stream:
                stream.write('x')
        assert target.read_text() == 'abcd'
        target.unlink()
        with pytest.raises(WorkflowHalt, match='quota_storage_write_bytes_limit'):
            with quota_open(target, 'a', encoding='utf-8') as stream:
                stream.write('x')
    with ledger.transaction() as db:
        assert quotas.usage(db, user['id'], time.time())['storage_write_bytes'] == 8


def test_graph_write_budget_precedes_database_side_effect(quota_app):
    from app.services.quota_io import GraphTransaction
    app, client, user, headers = quota_app
    configure(app, client, user, headers, individual=policy(storage_write_bytes=0))
    calls = []
    class Transaction:
        def run(self, *args, **kwargs): calls.append(args)
    with w.workspace_scope(user['id']):
        tx = GraphTransaction(Transaction())
        tx.run('MATCH (n) RETURN n')
        with pytest.raises(WorkflowHalt, match='quota_storage_write_bytes_limit'):
            tx.run('CREATE (n {text:$text})', text='fictional')
    assert len(calls) == 1


def test_storage_guard_accounts_for_text_newline_translation(quota_app, tmp_path):
    from app.services.quota_io import open as quota_open
    app, client, user, headers = quota_app
    configure(app, client, user, headers, individual=policy(storage_write_bytes=4))
    target = tmp_path / 'translated.txt'
    with w.workspace_scope(user['id']):
        with pytest.raises(WorkflowHalt, match='quota_storage_write_bytes_limit'):
            with quota_open(target, 'w', encoding='utf-8', newline='\r\n') as stream:
                stream.write('a\nb\n')
    assert not target.exists()


def test_http_transport_retries_share_quota_and_return_429_without_extra_call(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(requests=1))
    wid = client.post('/api/execution/authorize', json=authorization(), headers=headers).json['data']['workflow_id']
    r = client.post('/api/report/generate', json={'workflow_id': wid, 'calls': 2}, headers=headers)
    assert r.status_code == 429
    assert r.json['error'] == 'quota_requests_limit'
    with w.workspace_scope(user['id']):
        status = ledger.status(wid)
        assert status['admitted'] == 1
        assert status['quotas']['reason'] == 'quota_requests_limit'
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['active_work'] == 0


def test_http_request_hands_its_active_slot_to_background_task(quota_app):
    app, client, user, headers = quota_app
    configure(app, client, user, headers, individual=policy(active_work=1))
    r = client.post('/api/start-task', json={}, headers=headers)
    assert r.status_code == 200, r.json
    assert client.post('/api/start-task', json={}, headers=headers).status_code == 429
    with w.workspace_scope(user['id']):
        TaskManager().complete_task(r.json['task_id'], {'fixture': True})
    assert client.post('/api/start-task', json={}, headers=headers).status_code == 200


def test_concurrent_storage_publication_cannot_exceed_shared_byte_allowance(quota_app, tmp_path):
    from app.services.quota_io import open as quota_open
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, shared=policy(global_scope=True, storage_write_bytes=8))
    def write(number):
        try:
            with w.workspace_scope(user['id']), quota_open(tmp_path / f'{number}.txt', 'w') as stream:
                stream.write('abc')
            return True
        except WorkflowHalt:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        result = list(pool.map(write, range(12)))
    assert result.count(True) == 2
    assert sum(p.stat().st_size for p in tmp_path.glob('*.txt')) == 6
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['storage_write_bytes'] == 6


def test_reconciliation_records_provider_statement_without_refunding_unknowns(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    with w.workspace_scope(user['id']):
        physical(ledger, new_workflow(ledger))
    now = int(time.time())
    receipt = dict(period_start=now-60, period_end=now+1, reported_micro_usd=0, reported_requests=1,
                   reference='Synthetic provider statement; not a live billing reconciliation')
    r = client.post('/api/execution/quotas/reconciliation', json=receipt, headers=headers)
    assert r.status_code == 200, r.json
    assert r.json['data']['reserved_micro_usd'] == 50_000
    assert client.get('/api/execution/quotas/reconciliation').json['data'][0]['id'] == r.json['data']['id']
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['reserved_micro_usd'] == 50_000


def test_workflow_churn_is_bounded_but_idempotent_replay_is_free(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(operations=1))
    with w.workspace_scope(user['id']):
        first = new_workflow(ledger)
        assert new_workflow(WorkflowLedger(ledger.path)) == first
        with pytest.raises(WorkflowHalt, match='quota_operations_limit'):
            new_workflow(ledger, 'second')


def test_policy_roundtrip_cannot_disable_managed_mode_or_reset_usage(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    with w.workspace_scope(user['id']):
        physical(ledger, new_workflow(ledger))
    payload = client.get('/api/execution/quotas/global').json['data']['policy']
    payload['admission_open'] = False
    assert client.put('/api/execution/quotas/global', json=payload, headers=headers).status_code == 200
    restarted = WorkflowLedger(ledger.path, quotas_required=False)
    with restarted.transaction() as db:
        assert quotas.managed(db) is True
        assert quotas.usage(db, 'global', time.time())['requests'] == 1
    local_app = Flask('incorrect-local-restart')
    local_app.extensions['control_db'] = app.extensions['control_db']
    with pytest.raises(RuntimeError, match='require OIDC'):
        install_workflow_controls(local_app)


def test_administrator_price_change_preserves_authorization_replay_and_prices_new_attempts(quota_app):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    with w.workspace_scope(user['id']):
        wid = new_workflow(ledger)
    changed = policy(global_scope=True)
    changed['pricing']['reserve_usd'] = '0.10'
    changed['pricing']['input_usd_per_million'] = '2'
    assert client.put('/api/execution/quotas/global', json=changed, headers=headers).status_code == 200
    with w.workspace_scope(user['id']):
        assert new_workflow(ledger) == wid
        ticket = physical(ledger, wid)
        with ledger.transaction() as db:
            assert quotas.usage(db, 'global', time.time())['reserved_micro_usd'] == 100_000
        ledger.finish(ticket, status='response', usage=dict(input_tokens=1, output_tokens=0))
        with ledger.transaction() as db:
            assert quotas.usage(db, 'global', time.time())['estimated_micro_usd'] == 2


def child_environment(app, ledger, user):
    return dict(PATH=os.environ['PATH'], PYTHONPATH=str(Path(__file__).resolve().parents[1]),
        PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1',
        CROWDLENS_QUOTA_DB=ledger.path, CROWDLENS_WORKSPACE_DB=app.config['AUTH_DB_PATH'],
        CROWDLENS_WORKSPACE_ID=user['id'])


def test_child_path_and_sqlite_worker_writes_share_durable_quota(quota_app, tmp_path):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    code = '''
from app.services.quota_subprocess import install
install()
import concurrent.futures, sqlite3, pathlib, sys
pathlib.Path(sys.argv[1]).write_text('fictional', encoding='utf-8')
def work():
    with sqlite3.connect(sys.argv[2]) as db:
        db.execute('CREATE TABLE notes (text TEXT)')
        db.execute('INSERT INTO notes VALUES (?)', ('synthetic SQLite worker data',))
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
    pool.submit(work).result()
import os,tempfile
fd,name=tempfile.mkstemp(dir=pathlib.Path(sys.argv[1]).parent)
with os.fdopen(fd,'wb') as stream:
    stream.write(b'fictional forecast memory')
    stream.flush()
    os.fsync(stream.fileno())
'''
    artifact, database = tmp_path / 'child.txt', tmp_path / 'child.sqlite'
    result = subprocess.run([sys.executable, '-c', code, str(artifact), str(database)],
        env=child_environment(app, ledger, user), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert artifact.read_text() == 'fictional'
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT text FROM notes').fetchone()[0] == 'synthetic SQLite worker data'
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['storage_write_bytes'] > len('fictional')


def test_child_restarts_cannot_refund_file_allowance(quota_app, tmp_path):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(storage_write_bytes=8))
    code = "from app.services.quota_subprocess import install; install(); import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])"
    env = child_environment(app, ledger, user)
    target = tmp_path / 'child.txt'
    first = subprocess.run([sys.executable, '-c', code, str(target), 'hello'], env=env, capture_output=True, text=True, timeout=30)
    assert first.returncode == 0, first.stderr
    denied = subprocess.run([sys.executable, '-c', code, str(target), 'four'], env=env, capture_output=True, text=True, timeout=30)
    assert denied.returncode != 0
    assert 'quota_storage_write_bytes_limit' in denied.stderr
    assert target.read_text() == 'hello'
    final = subprocess.run([sys.executable, '-c', code, str(target), 'abc'], env=env, capture_output=True, text=True, timeout=30)
    assert final.returncode == 0, final.stderr
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['storage_write_bytes'] == 8


def test_child_sqlite_rejects_oversized_mutation_before_database_write(quota_app, tmp_path):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(storage_write_bytes=100))
    database = tmp_path / 'child.sqlite'
    code = '''
from app.services.quota_subprocess import install
install()
import sqlite3,sys
from app.services.workflow_execution import WorkflowHalt
db=sqlite3.connect(sys.argv[1])
db.execute('CREATE TABLE notes (text TEXT)')
db.commit()
try:
    db.execute('INSERT INTO notes VALUES (?)', ('x'*1000,))
except WorkflowHalt:
    pass
else:
    raise AssertionError('unmetered SQLite write')
assert db.execute('SELECT COUNT(*) FROM notes').fetchone()[0] == 0
'''
    result = subprocess.run([sys.executable, '-c', code, str(database)], env=child_environment(app, ledger, user),
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT COUNT(*) FROM notes').fetchone()[0] == 0


def test_real_upload_writer_obeys_managed_storage_allowance(quota_app, tmp_path, monkeypatch):
    import io
    from werkzeug.datastructures import FileStorage
    from app.models.project import ProjectManager
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers, individual=policy(storage_write_bytes=8))
    monkeypatch.setattr(ProjectManager, 'PROJECTS_DIR', str(tmp_path/'projects'))
    monkeypatch.setattr(ProjectManager, '_repository', app.extensions['control_db'])
    with w.workspace_scope(user['id']):
        project = ProjectManager.create_project('fictional upload')
        ProjectManager.save_file_to_project(project.project_id, FileStorage(io.BytesIO(b'abcd'),filename='fictional.txt'), 'fictional.txt')
        with pytest.raises(WorkflowHalt, match='quota_storage_write_bytes_limit'):
            ProjectManager.save_file_to_project(project.project_id, FileStorage(io.BytesIO(b'123456789'),filename='oversized.txt'), 'oversized.txt')
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['storage_write_bytes'] == 4


def test_raw_child_stdout_is_bounded_before_log_publication(quota_app, tmp_path):
    from app.services.quota_subprocess import capture_stdout
    app, client, user, headers = quota_app
    configure(app, client, user, headers, individual=policy(storage_write_bytes=8))
    with w.workspace_scope(user['id']):
        process = subprocess.Popen([sys.executable, '-c', "import os; os.write(1,b'123456789')"], stdout=subprocess.PIPE)
        capture_stdout(process, tmp_path / 'simulation.log')
        process.wait(timeout=5)
        assert process._crowdlens_quota_error == 'quota_storage_write_bytes_limit'
        assert not (tmp_path / 'simulation.log').exists()


def test_real_oasis_sqlite_schema_initializes_under_managed_meter(quota_app, tmp_path):
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    code = '''
from app.services.quota_subprocess import install
install()
import importlib.util, pathlib, sys, sqlite3
root=pathlib.Path(importlib.util.find_spec('oasis').origin).parent
spec=importlib.util.spec_from_file_location('fixture_oasis_database',root/'social_platform/database.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.create_db(sys.argv[1])
db=sqlite3.connect(sys.argv[1])
assert db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] >= 10
'''
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path / 'oasis.sqlite')],
        env=child_environment(app, ledger, user), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    with ledger.transaction() as db:
        assert quotas.usage(db, 'global', time.time())['storage_write_bytes'] > 1000


def test_managed_launch_uses_bootstrap_and_a_metered_stdout_pipe(quota_app, tmp_path, monkeypatch):
    from types import SimpleNamespace
    import io
    from app.services.simulation_runner import SimulationRunner
    app, client, user, headers = quota_app
    ledger = configure(app, client, user, headers)
    sim_dir = tmp_path / 'synthetic'
    sim_dir.mkdir()
    (sim_dir / 'simulation_config.json').write_text(json.dumps({'time_config':{'total_simulation_hours':1,'minutes_per_round':60}}))
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    for name in ('_run_states', '_processes', '_stdout_files', '_stderr_files', '_graph_memory_enabled', '_monitor_threads'):
        monkeypatch.setattr(SimulationRunner, name, {})
    monkeypatch.setattr(SimulationRunner, '_repository', app.extensions['control_db'])
    monkeypatch.setattr(SimulationRunner, '_monitor_simulation', lambda *args: None)
    launched = []
    def launch(command, **kwargs):
        launched.append((command, kwargs))
        return SimpleNamespace(pid=12345, stdout=io.BytesIO(b'synthetic output'))
    monkeypatch.setattr('app.services.simulation_runner.subprocess.Popen', launch)
    with w.workspace_scope(user['id']):
        w.register('simulation', 'synthetic')
        SimulationRunner.start_simulation('synthetic', max_rounds=1)
    command, arguments = launched[0]
    assert Path(command[1]).name == 'quota_runner.py'
    assert Path(command[2]).name == 'run_parallel_simulation.py'
    assert arguments['env']['CROWDLENS_QUOTA_DB'] == ledger.path
    assert arguments['stdout'] == subprocess.PIPE
    assert arguments['text'] is False
    process = SimulationRunner._processes['synthetic']
    process._crowdlens_output_thread.join(timeout=5)
    assert (sim_dir / 'simulation.log').read_bytes() == b'synthetic output'


def test_quota_closure_of_idle_environment_preserves_completed_outcome(quota_app, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    app, client, user, headers = quota_app
    configure(app, client, user, headers)
    process = SimpleNamespace(poll=lambda:0, returncode=0, _crowdlens_quota_error='quota_storage_write_bytes_limit')
    state = SimulationRunState('synthetic', runner_status=RunnerStatus.COMPLETED)
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    monkeypatch.setattr(SimulationRunner, '_processes', {'synthetic':process})
    monkeypatch.setattr(SimulationRunner, '_graph_memory_enabled', {})
    monkeypatch.setattr(SimulationRunner, '_stdout_files', {})
    monkeypatch.setattr(SimulationRunner, '_stderr_files', {})
    monkeypatch.setattr(SimulationRunner, '_save_run_state', lambda *args: None)
    with w.workspace_scope(user['id']):
        w.register('simulation', 'synthetic')
        SimulationRunner._monitor_simulation('synthetic', process, state)
    assert state.runner_status == RunnerStatus.COMPLETED
    assert state.execution['quota_close_reason'] == 'quota_storage_write_bytes_limit'
