import json
import multiprocessing as mp
import os
import pytest
from pathlib import Path


def test_retry_and_reuse(tmp_path):
    from app.services.proposal_store import ProposalStore, ProposalError
    store = ProposalStore(tmp_path)
    first, lease = store.admit('report_root', 'request-1', 'digest')
    try:
        second, repeated = ProposalStore(tmp_path).admit('report_root', 'request-1', 'digest')
        assert first == second and repeated is None
        with pytest.raises(ProposalError, match='idempotency_conflict'):
            store.admit('report_root', 'request-1', 'other')
        with pytest.raises(ProposalError, match='report_busy'):
            store.admit('report_root', 'request-2', 'digest')
    finally:
        lease.close()


def test_capacity_and_rejection_fence(tmp_path):
    from app.services.proposal_store import ProposalStore, ProposalError
    store = ProposalStore(tmp_path)
    a, lease_a = store.admit('report_a', 'a', 'a')
    b, lease_b = store.admit('report_b', 'b', 'b')
    try:
        with pytest.raises(ProposalError, match='capacity'):
            store.admit('report_c', 'c', 'c')
        store.reject('report_a', a['proposal_id'])
        with pytest.raises(ProposalError, match='state_conflict'):
            store.finish(a['proposal_id'], {'state': 'ready'})
        assert store.get('report_a', a['proposal_id'])['state'] == 'rejected'
        with pytest.raises(ProposalError, match='not_found'):
            store.get('report_b', a['proposal_id'])
    finally:
        lease_a.close()
        lease_b.close()


def hold_child(root, conn, running):
    from app.services.proposal_store import ProposalStore
    store = ProposalStore(root)
    record, lease = store.admit('report_child', 'child', 'body')
    if running:
        store.update(record['proposal_id'], {'queued'}, {'state': 'running'})
    conn.send(record['proposal_id'])
    conn.recv()
    lease.close()


@pytest.mark.parametrize('running', [False, True])
def test_restart_only_reconciles_abandoned_process(tmp_path, running):
    from app.services.proposal_store import ProposalStore
    parent, child = mp.Pipe()
    worker = mp.Process(target=hold_child, args=(str(tmp_path), child, running))
    worker.start()
    identifier = parent.recv()
    store = ProposalStore(tmp_path)
    assert store.reconcile()['interrupted'] == 0
    worker.terminate()
    worker.join(5)
    assert store.reconcile()['interrupted'] == 1
    assert store.get('report_child', identifier)['state'] == 'failed'
    assert store.reconcile()['interrupted'] == 0


def test_snapshot_hash_and_path_safety(tmp_path):
    from app.services.proposal_store import ProposalStore, ProposalError
    store = ProposalStore(tmp_path)
    with pytest.raises(ProposalError):
        store.admit('../outside', 'key', 'body')
    record, lease = store.admit('report_a', 'a', 'a')
    lease.close()
    identifier = record['proposal_id']
    digest = store.save_snapshot(identifier, 'parent', {'secret': 'fixture'})
    assert store.load_snapshot(identifier, 'parent', digest) == {'secret': 'fixture'}
    with pytest.raises(ProposalError, match='snapshot_mismatch'):
        store.load_snapshot(identifier, 'parent', 'bad')
    path = tmp_path / '.evidence-proposals' / identifier / 'parent.json'
    path.unlink()
    path.symlink_to(tmp_path / 'outside.json')
    with pytest.raises(ProposalError, match='unsafe_path'):
        store.save_snapshot(identifier, 'parent', {})
