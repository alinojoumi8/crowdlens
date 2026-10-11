"""No model calls: physical transport fakes and separate SQLite processes."""
import concurrent.futures
import multiprocessing
import pytest

from app.services.workflow_execution import WorkflowLedger, WorkflowHalt
from app.services.workflow_spend import micro_usd, estimated_micro_usd

BASE = 'http://127.0.0.1:1/anthropic'


def prices(**overrides):
    return dict(currency='USD', budget_usd='0.10', reserve_usd='0.05',
                input_usd_per_million='1.25', output_usd_per_million='10',
                price_reference='Fictional rates v1; not MiniMax pricing', **overrides)


def authorize(ledger, spend=None, **overrides):
    return ledger.authorize(request_key='budget', provider='synthetic', model='synthetic',
        base_url=BASE, input_description='fictional', max_requests=100, max_seconds=300,
        confirmed=True, spend=spend or prices(), **overrides)['workflow_id']


def admit(ledger, wid):
    return ledger.admit(wid, 1, 'report', 'synthetic', BASE)


def process_admit(args):
    path, wid = args
    try:
        return admit(WorkflowLedger(path), wid)
    except WorkflowHalt as exc:
        return exc.reason


def test_atomic_money_admission_across_processes_and_restart(tmp_path):
    path = tmp_path / 'control.sqlite'
    ledger = WorkflowLedger(path)
    wid = authorize(ledger)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn')) as pool:
        results = list(pool.map(process_admit, [(path, wid)] * 12))
    assert sum(isinstance(result, dict) for result in results) == 2
    assert set(r for r in results if isinstance(r, str)) == {'spend_limit'}
    status = WorkflowLedger(path).status(wid)
    assert status['spend']['reserved_micro_usd'] == 100_000
    assert status['spend']['available_micro_usd'] == 0
    assert status['admitted'] == 2
    assert authorize(ledger) == wid
    assert ledger.status(wid)['spend'] == status['spend']
    assert status['initial_authorization']['spend']['budget_micro_usd'] == 100_000
    assert 'reserved_micro_usd' not in status['initial_authorization']['spend']


def test_complete_usage_releases_reservation_exactly_once(tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite'); wid = authorize(ledger)
    ticket = admit(ledger, wid)
    usage = dict(input_tokens=10, output_tokens=2, cache_creation_input_tokens=3, cache_read_input_tokens=7)
    ledger.finish(ticket, status='response', usage=usage)
    ledger.finish(ticket, status='response', usage=dict(input_tokens=1000000, output_tokens=1000000))
    after = ledger.status(wid)
    assert after['spend']['estimated_micro_usd'] == 45
    assert after['spend']['reserved_micro_usd'] == 0
    assert after['spend']['available_micro_usd'] == 99_955
    assert after['billing_amount'] is None
    assert after['attempts'][0]['spend']['estimated_micro_usd'] == 45
    assert admit(ledger, wid)


@pytest.mark.parametrize('usage', [None, {}, {'input_tokens':1}, {'input_tokens':-1,'output_tokens':2},
    {'input_tokens':True,'output_tokens':2}, {'input_tokens':float('nan'),'output_tokens':2},
    {'input_tokens':1.2,'output_tokens':2}, {'input_tokens':1,'output_tokens':2,'cache_read_input_tokens':None}])
def test_unknown_usage_retains_reservation(tmp_path, usage):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite'); wid = authorize(ledger)
    ticket = admit(ledger, wid)
    ledger.finish(ticket, status='delivery_or_usage_unknown', usage=usage)
    status = ledger.status(wid)
    assert status['spend']['reserved_micro_usd'] == 50_000
    assert status['spend']['estimated_micro_usd'] == 0
    assert status['spend']['unpriced_attempts'] == 1


def test_stop_accepts_late_usage_without_reopening_or_resetting_money(tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite'); wid = authorize(ledger)
    ticket = admit(ledger, wid); ledger.stop(wid)
    ledger.finish(ticket, status='response', usage=dict(prompt_tokens=1, completion_tokens=1))
    status = WorkflowLedger(ledger.path).status(wid)
    assert status['state'] == 'stopped'
    assert status['spend']['estimated_micro_usd'] == 12
    assert status['spend']['reserved_micro_usd'] == 0
    with pytest.raises(WorkflowHalt, match='stopped'): admit(ledger, wid)


def test_estimate_above_reservation_closes_admission_and_is_visible(tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite'); wid = authorize(ledger)
    ticket = admit(ledger, wid)
    ledger.finish(ticket, status='response', usage=dict(input_tokens=100000, output_tokens=10000))
    status = ledger.status(wid)
    assert status['state'] == 'spend_estimate_exceeded'
    assert status['spend']['estimated_micro_usd'] == 225_000
    assert status['spend']['available_micro_usd'] == 0
    assert status['spend']['overrun_attempts'] == 1
    with pytest.raises(WorkflowHalt, match='spend_estimate_exceeded'): admit(ledger, wid)
    with pytest.raises(WorkflowHalt, match='spend_estimate_exceeded'): ledger.checkpoint(wid, 1)


def test_renewal_includes_unknown_reservations_and_freezes_rates(tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite'); wid = authorize(ledger)
    ticket = admit(ledger, wid); ledger.stop(wid)
    terms = dict(max_requests=101, max_seconds=60, confirmed=True, request_key='renew')
    with pytest.raises(ValueError, match='explicit_spend_budget_required'): ledger.reauthorize(wid, **terms)
    with pytest.raises(ValueError, match='budget_cannot_reserve'): ledger.reauthorize(wid, budget_usd='0.05', **terms)
    with pytest.raises(ValueError, match='acknowledge_in_flight'): ledger.reauthorize(wid, budget_usd='0.20', **terms)
    assert ledger.status(wid)['spend']['budget_micro_usd'] == 100_000
    renewed = ledger.reauthorize(wid, budget_usd='0.20', acknowledge_unknown=True, **terms)
    assert renewed['epoch'] == 2
    assert ledger.reauthorize(wid, budget_usd='0.20', acknowledge_unknown=True, **terms)['epoch'] == 2
    with pytest.raises(ValueError, match='reauthorization_key_conflict'):
        ledger.reauthorize(wid, budget_usd='0.30', acknowledge_unknown=True, **terms)
    assert renewed['spend']['reserved_micro_usd'] == 50_000
    assert renewed['spend']['input_rate_micro_usd'] == 1_250_000
    assert renewed['initial_authorization']['spend']['budget_micro_usd'] == 100_000
    # The old request still settles into the same root after renewal.
    ledger.finish(ticket, status='response', usage=dict(input_tokens=2, output_tokens=2))
    assert ledger.status(wid)['spend']['reserved_micro_usd'] == 0
    assert ledger.status(wid)['spend']['estimated_micro_usd'] == 23


@pytest.mark.parametrize('value', [True, 1, 0.1, '-1', 'NaN', 'Infinity', '1e-6', '0.0000001', '1000001', '', ' 1'])
def test_usd_requires_bounded_exact_decimal_strings(value):
    with pytest.raises(ValueError): micro_usd(value)


def test_rounding_cache_accounting_and_legacy_boundaries(tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite'); wid = authorize(ledger)
    p = ledger.status(wid)['spend']
    assert estimated_micro_usd(dict(prompt_tokens=1, completion_tokens=0, prompt_tokens_details={'cached_tokens':1}), p) == 2
    with pytest.raises(ValueError, match='legacy_usage_cannot_be_priced'): authorize(ledger, consumed_requests=1)
    altered = prices(); altered['price_reference'] = 'changed'
    with pytest.raises(ValueError, match='authorization_key_conflict'): authorize(ledger, altered)
    plain = ledger.authorize(request_key='plain', provider='synthetic', model='synthetic', base_url=BASE,
        input_description='fictional', max_requests=10, max_seconds=60, confirmed=True)['workflow_id']
    with pytest.raises(ValueError, match='cannot_add_pricing'):
        ledger.reauthorize(plain, max_requests=20, max_seconds=60, confirmed=True, budget_usd='1', request_key='new')
