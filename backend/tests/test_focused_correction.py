import copy
from types import SimpleNamespace
import pytest
from evidence_draft_samples import SCOPE, sample_report
from app.services.evidence_drafting import EvidenceDraftingService
from app.services.focused_correction import validate_request
from app.services.proposal_store import ProposalStore, ProposalError, proposal_digest
from app.services.report_agent import ReportManager
from app.services.report_revisions import ReportRevisionService
from app.utils.draft_budget import DraftBudget

CORRECTION = {'old_text': 'May 29, 2025', 'new_text': 'May 29, 2023',
              'source_quote': 'In the May 29, 2023 affidavit, Alex denies signing.'}


class Sources:
    text = CORRECTION['source_quote'] + ' He could agree only if an original is produced.'
    def get_source_chunks(self, **scope):
        return [{**SCOPE, 'uuid': 'one', 'document_id': 'doc', 'data': self.text, 'page': 6}]


def run(tmp_path, monkeypatch, outcome='supported'):
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    parent = sample_report()
    parent.outline.sections[0].content = 'Alex denies signing in the May 29, 2025 affidavit. Check the May 29, 2025 affidavit. He could agree only if an original is produced.'
    ReportManager.save_report(parent)
    store = ProposalStore(tmp_path)
    record, lease = store.admit('report_root', 'focused', 'request')
    store.update(record['proposal_id'], {'queued'}, {'state': 'running', 'scope': SCOPE, 'section_index': 1, 'focused_correction': CORRECTION})
    llm = SimpleNamespace(model='synthetic', chat_json=lambda *a, **kw: {'outcome': outcome, 'detail': 'Both references identify the same affidavit; denial and condition are preserved.'})
    sources = Sources()
    try:
        result = EvidenceDraftingService(sources, llm, store).generate(record['proposal_id'], parent.to_dict(), budget=DraftBudget(seconds=10))
    finally:
        lease.close()
    return parent, store, sources, result


def test_focused_revision_preserves_conditions_summary_parent_and_seals_patch(tmp_path, monkeypatch):
    parent, store, sources, result = run(tmp_path, monkeypatch)
    assert result['state'] == 'ready'
    assert result['replacement_count'] == 2
    assert result['after']['section'] == parent.outline.sections[0].content.replace('2025', '2023')
    revision = ReportRevisionService(store, storage=sources).accept('report_root', result['proposal_id'], result['proposal_digest'])
    assert revision.outline.summary == parent.outline.summary
    assert revision.outline.sections[1].content == parent.outline.sections[1].content
    assert ReportManager.get_report('report_root').to_dict() == parent.to_dict()
    assert revision.status.value == 'needs_review'
    assert 'inherited' in revision.revision['review_scope']
    with pytest.raises(ProposalError, match='immutable_proposal'):
        store.update(result['proposal_id'], {'accepted'}, {'focused_correction': {}})
    tampered = copy.deepcopy(result); tampered['focused_correction']['new_text'] = 'May 29, 2022'
    assert proposal_digest(tampered) != result['proposal_digest']


@pytest.mark.parametrize('outcome', ['unsupported', 'unverified'])
def test_negative_focused_audit_cannot_publish(tmp_path, monkeypatch, outcome):
    _, store, sources, result = run(tmp_path, monkeypatch, outcome)
    assert result['state'] == 'blocked'
    with pytest.raises(ProposalError):
        ReportRevisionService(store, storage=sources).accept('report_root', result['proposal_id'], result['proposal_digest'])


def test_changed_original_sources_block_acceptance(tmp_path, monkeypatch):
    _, store, sources, result = run(tmp_path, monkeypatch)
    sources.text += ' Later contradictory evidence.'
    with pytest.raises(ProposalError, match='stale_sources'):
        ReportRevisionService(store, storage=sources).accept('report_root', result['proposal_id'], result['proposal_digest'])


@pytest.mark.parametrize('change', [
    {'new_text': 'May 29, 2023; signing admitted'}, {'new_text': 'May 29, 2022'},
    {'old_text': 'could agree', 'new_text': 'will agree'}, {'source_quote': ''}])
def test_only_literal_corrections_supported_by_quotation_allowed(change):
    with pytest.raises(ValueError):
        validate_request({**CORRECTION, **change})
