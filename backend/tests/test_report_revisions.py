import json
import shutil
from pathlib import Path
import pytest
from evidence_draft_samples import sample_report
from test_evidence_drafting import run, SourceStorage
from app.services.report_agent import ReportManager, ReportStatus, ReportAgent
from app.services.proposal_store import ProposalStore, ProposalError


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    ReportManager.save_report(sample_report())
    return tmp_path


def ready(root):
    record, _ = run(root)
    from app.services.report_revisions import ReportRevisionService
    return record, ReportRevisionService(ProposalStore(root), storage=SourceStorage())


def test_accept_is_immutable_and_preserves_parent_and_other_text(root):
    record, service = ready(root)
    original = {p.name: p.read_bytes() for p in (root/'report_root').iterdir()}
    revision = service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    assert revision.report_id != 'report_root'
    loaded = ReportManager.get_report(revision.report_id)
    assert loaded.status == ReportStatus.NEEDS_REVIEW
    assert loaded.outline.sections[1].content == sample_report().outline.sections[1].content
    assert loaded.forecast == sample_report().forecast
    assert loaded.revision['inherited_forecast']
    assert loaded.outline.sections[0].claim_ledger
    assert {p.name:p.read_bytes() for p in (root/'report_root').iterdir()} == original
    assert service.accept('report_root', record['proposal_id'], record['proposal_digest']) == revision
    ReportManager.apply_quality_status(loaded)
    assert loaded.status == ReportStatus.NEEDS_REVIEW
    with pytest.raises(ProposalError, match='immutable_revision'):
        ReportManager.save_report(loaded)
    agent = ReportAgent.__new__(ReportAgent)
    for method, kwargs in [(agent.resume_report, {}), (agent.regenerate_section, {'section_index': 1})]:
        with pytest.raises(ProposalError, match='immutable_revision'):
            method(loaded, **kwargs)


def test_crash_after_publication_recovers_without_parent_or_sources(root, monkeypatch):
    record, service = ready(root)
    original = service.store.update
    def fail_accept(identifier, expected, changes):
        if changes.get('state') == 'accepted':
            raise OSError('simulated crash')
        return original(identifier, expected, changes)
    monkeypatch.setattr(service.store, 'update', fail_accept)
    with pytest.raises(OSError):
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    shutil.rmtree(root/'report_root')
    monkeypatch.setattr(service.store, 'update', original)
    service.storage = None
    revision = service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    assert revision.report_id == record['revision_report_id']
    ReportManager.delete_report(revision.report_id)
    with pytest.raises(ProposalError) as exc:
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    assert exc.value.status == 410
    assert not (root / revision.report_id).exists()


def test_changed_parent_blocks_without_publication(root):
    record, service = ready(root)
    parent = ReportManager.get_report('report_root')
    parent.outline.summary = 'Changed summary.'
    ReportManager.save_report(parent)
    with pytest.raises(ProposalError, match='stale_parent'):
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    assert service.store.read(record['proposal_id'])['state'] == 'stale'
    assert not (root / record['revision_report_id']).exists()


def test_lookup_never_returns_revision_and_filters_mode(root):
    record, service = ready(root)
    service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    newer = sample_report('report_newer'); newer.created_at = '2026-09-22'; newer.report_mode = 'prediction'
    ReportManager.save_report(newer)
    assert ReportManager.get_report_by_simulation('sim_1').report_id == 'report_newer'
    assert ReportManager.get_report_by_simulation('sim_1', report_mode='legal_case').report_id == 'report_root'
    ReportManager.delete_report('report_newer'); ReportManager.delete_report('report_root')
    assert ReportManager.get_report_by_simulation('sim_1') is None
    assert len(ReportManager.list_reports()) == 1


def test_source_outage_keeps_ready_and_source_change_stales(root):
    record, service = ready(root)
    service.storage = None
    with pytest.raises(ProposalError) as exc:
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    assert exc.value.status == 503 and service.store.read(record['proposal_id'])['state'] == 'ready'
    class Changed:
        def get_source_chunks(self, **kw): return []
    service.storage = Changed()
    with pytest.raises(ProposalError, match='stale_sources'):
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])


def test_reject_after_publish_and_tampered_output(root):
    record, service = ready(root)
    revision = service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    with pytest.raises(ProposalError, match='already_accepted'):
        service.reject('report_root', record['proposal_id'])
    (root/revision.report_id/'full_report.md').write_text('tampered')
    with pytest.raises(ProposalError, match='revision_conflict'):
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])


def test_legacy_mutation_and_deletion_share_proposal_lease(root):
    store = ProposalStore(root)
    _, lease = store.admit('report_root', 'active', 'body')
    try:
        with pytest.raises(ProposalError, match='report_busy'):
            ReportManager.delete_report('report_root')
        with pytest.raises(ProposalError, match='report_busy'):
            ReportAgent.__new__(ReportAgent).regenerate_section(sample_report(), 1)
    finally:
        lease.close()


@pytest.mark.parametrize('operation', ['outline', 'section', 'progress', 'assemble'])
def test_low_level_writers_reject_immutable_revision(root, operation):
    record, service = ready(root)
    revision = service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    calls = {'outline': lambda: ReportManager.save_outline(revision.report_id, revision.outline),
             'section': lambda: ReportManager.save_section(revision.report_id, 1, revision.outline.sections[0]),
             'progress': lambda: ReportManager.update_progress(revision.report_id, 'completed', 100, 'modified'),
             'assemble': lambda: ReportManager.assemble_full_report(revision.report_id, revision.outline)}
    with pytest.raises(ProposalError, match='immutable_revision'):
        calls[operation]()


def test_report_file_symlink_cannot_escape_root(root, tmp_path):
    outside = root/'outside.json'
    outside.write_text(json.dumps(sample_report('outside').to_dict()))
    metadata = root/'report_root'/'meta.json'
    metadata.unlink(); metadata.symlink_to(outside)
    with pytest.raises(ProposalError, match='unsafe_path'):
        ReportManager.get_report('report_root')


def test_generate_cannot_reuse_immutable_revision_id(root):
    record, service = ready(root)
    revision = service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    with pytest.raises(ProposalError, match='immutable_revision'):
        ReportAgent.__new__(ReportAgent).generate_report(report_id=revision.report_id)


def test_rejection_recovers_interrupted_prepublication_save(root, monkeypatch):
    record, service = ready(root)
    monkeypatch.setattr(service, '_publish', lambda *args: (_ for _ in ()).throw(OSError('disk-full')))
    with pytest.raises(OSError):
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    assert service.store.read(record['proposal_id'])['state'] == 'accepting'
    assert service.reject('report_root', record['proposal_id'])['state'] == 'rejected'


def test_concurrent_storage_probes_do_not_switch_report_roots(tmp_path, monkeypatch):
    import os
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    primary, fallback = tmp_path/'primary', tmp_path/'fallback'
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(primary))
    monkeypatch.setattr(ReportManager, 'FALLBACK_REPORTS_DIR', str(fallback))
    barrier, remove = Barrier(2), os.remove
    def concurrent_remove(path):
        if Path(path).parent == primary and Path(path).name.startswith('.write_test_'):
            barrier.wait(timeout=5)
        return remove(path)
    monkeypatch.setattr(os, 'remove', concurrent_remove)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ReportManager._get_reports_dir(), range(2)))
    assert results == [str(primary), str(primary)]
    assert not fallback.exists()
