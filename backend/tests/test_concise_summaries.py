"""Concise summary validation and frozen source links."""
import json
import pytest
from test_evidence_drafting import run, SourceStorage
from test_report_revisions import root, ready
from app.services.report_agent import ReportManager
from app.services.proposal_store import ProposalError, proposal_digest


def test_page_length_summary_stops_before_audit(tmp_path):
    result, llm = run(tmp_path, {'EVIDENCE_DRAFT_V1': {
        'paragraphs': [{'text': 'Alex says the hearing was postponed.', 'kind': 'attributed_allegation', 'claim_ids': ['claim_01']}],
        'section_summary': {'text': 'A' * 601, 'claim_ids': ['claim_01']}}})
    assert result['state'] == 'blocked'
    assert llm.calls[-1] == 'EVIDENCE_DRAFT_V1'
    assert any(f.get('detail') == 'summary_too_long' for f in result['findings'])


def test_saved_summary_sources_and_download_survive_reload(root):
    record, service = ready(root)
    revision = service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    loaded = ReportManager.get_report(revision.report_id)
    passage = loaded.revision['summary_sources'][0]
    assert passage['text'] == record['summary_edits'][0]['new_text']
    assert passage['sources'] == record['sources']
    assert '[Source 1](#summary-source-1-1)' in loaded.markdown_content
    assert 'id="summary-source-1-1"' in loaded.markdown_content
    assert (root / revision.report_id / 'full_report.md').read_text() == loaded.markdown_content


def test_accept_rechecks_concise_limit(root):
    record, service = ready(root)
    record['summary_edits'][0]['new_text'] = 'A' * 601
    record['after']['summary'] = 'A' * 601 + ' Other issues remain open.'
    record['proposal_digest'] = proposal_digest(record)
    service.store._file(record['proposal_id'], 'record').write_text(json.dumps(record))
    with pytest.raises(ProposalError, match='invalid_proposal'):
        service.accept('report_root', record['proposal_id'], record['proposal_digest'])


def test_short_paraphrase_still_requires_audit(tmp_path):
    result, llm = run(tmp_path, {'EVIDENCE_AUDIT_V1': {
        'audit_protocol': 'target_reviews_v1', 'summary_consistent': False,
        'summary_assessment': {'outcome': 'contradicted', 'detail': 'The source does not establish this summary.', 'evidence_ids': ['episode:one']},
        'paragraph_reviews': [{'target_index': 0, 'outcome': 'supported', 'detail': 'Source matches.'}],
        'summary_reviews': [{'target_index': 0, 'outcome': 'unsupported', 'detail': 'Source does not establish this.'}],
        'document_reviews': [{'document_id': 'doc', 'outcome': 'complete', 'detail': 'Covered.'}],
        'claim_reviews': [{'claim_id': 'claim_01', 'outcome': 'supported', 'evidence_ids': ['episode:one'], 'detail': 'Source matches.'}]}})
    assert result['state'] == 'blocked'
    assert llm.calls[-1] == 'EVIDENCE_AUDIT_V1'
    assert any(f['blocking'] for f in result['findings'])


def test_summary_source_chains_reject_missing_or_cyclic_premises():
    from app.services.summary_sources import summary_sources
    source = {'evidence_id': 's1', 'document_id': 'd1'}
    record = {'ledger': [
        {'claim_id': 'source', 'citation_ids': ['s1'], 'premise_claim_ids': []},
        {'claim_id': 'analysis', 'citation_ids': [], 'premise_claim_ids': ['source']}],
        'sources': [source], 'summary_edits': [{'start': 0, 'end': 3, 'new_text': 'Bounded inference.', 'claim_ids': ['analysis', 'source']}]}
    assert summary_sources(record) == [{'text': 'Bounded inference.', 'start': 0, 'end': 18, 'sources': [source]}]
    record['ledger'][0]['premise_claim_ids'] = ['analysis']
    with pytest.raises(ValueError, match='invalid_summary_claim_chain'):
        summary_sources(record)
    record['ledger'][0]['premise_claim_ids'] = ['missing']
    with pytest.raises(ValueError, match='invalid_summary_claim_chain'):
        summary_sources(record)


def test_download_escapes_source_markup():
    from app.services.summary_sources import summary_sources_markdown
    text = summary_sources_markdown([{'text': '[click](https://example.invalid)', 'sources': [
        {'filename': '<script>bad</script>.pdf', 'document_id': 'd',
         'window': '<img src=x>\n[click](https://example.invalid)', 'locator': {'page': 1}}]}])
    assert '<script>' not in text and '<img' not in text
    assert '[click](https://example.invalid)' not in text
    assert '[Source 1](#summary-source-1-1)' in text


def test_new_format_is_digest_bound_and_legacy_keeps_its_limit(root):
    from app.services.summary_sources import validate_concise_summary
    record, service = ready(root)
    original = record['proposal_digest']
    record.pop('summary_format')
    assert proposal_digest(record) != original
    record['summary_edits'][0]['new_text'] = 'A' * 601
    validate_concise_summary(record)


def test_large_guarded_page_gets_short_audited_summary(tmp_path, monkeypatch):
    from test_evidence_drafting import FakeLLM
    from evidence_draft_samples import SCOPE
    page = ('Fictional committee record. ' * 50) + 'Alex said the group could assist if funding is confirmed.'
    short = 'Alex said the group could assist if funding is confirmed.'
    monkeypatch.setattr(SourceStorage, 'get_source_chunks', lambda self, **scope: [
        {**SCOPE, 'uuid': 'one', 'document_id': 'doc', 'data': page, 'page': 1}])
    original = FakeLLM.chat_json
    def chat(self, messages, **kwargs):
        context = json.loads(messages[1]['content'])
        phase = messages[0]['content'].splitlines()[0]
        if phase == 'EVIDENCE_DRAFT_V1':
            assert 'at most 600 characters' in messages[0]['content']
            claim = context['ledger'][0]
            self.calls.append(phase)
            return {'paragraphs': [{'text': claim['text'], 'kind': claim['kind'], 'claim_ids': [claim['claim_id']]}],
                    'section_summary': {'text': short, 'claim_ids': [claim['claim_id']]}}
        if phase == 'EVIDENCE_AUDIT_V1':
            assert context['summary_edits'][0]['new_text'] == short
            assert context['ledger'][0]['text'] == page
            audit = original(self, messages, **kwargs)
            audit['claim_reviews'][0]['claim_id'] = context['ledger'][0]['claim_id']
            return audit
        return original(self, messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    result, llm = run(tmp_path)
    assert result['state'] == 'ready'
    assert llm.calls == ['EVIDENCE_DRAFT_V1', 'EVIDENCE_AUDIT_V1']
    assert result['after']['summary'] == short + ' Other issues remain open.'
    assert page in result['after']['section']


def test_inherited_links_follow_offsets_and_disappear_only_when_changed(root):
    from app.services.summary_sources import revision_summary_sources
    from copy import deepcopy
    record, service = ready(root)
    parent = service.accept('report_root', record['proposal_id'], record['proposal_digest'])
    inherited = deepcopy(parent.revision['summary_sources'])
    unchanged = {**record, 'summary_edits': []}
    assert revision_summary_sources(parent, unchanged) == inherited
    # An insertion before the linked passage must shift its link, not erase it.
    edited = {**record, 'summary_edits': [{'start': 0, 'end': 0, 'old_text': '',
        'new_text': 'Brief. ', 'claim_ids': ['claim_01']}]}
    shifted = revision_summary_sources(parent, edited)
    assert shifted[1]['text'] == inherited[0]['text']
    assert shifted[1]['start'] == 7 and shifted[1]['end'] == inherited[0]['end'] + 7
    edited['summary_edits'][0].update(start=1, end=2)
    assert len(revision_summary_sources(parent, edited)) == 1
    edited['summary_edits'][0].update(start=2, end=2)
    assert len(revision_summary_sources(parent, edited)) == 1
    # Saving another revision with no summary change must persist inherited links.
    next_record = {**record, 'summary_edits': [], 'after': {**record['after'], 'summary': parent.outline.summary}}
    assembled = service._assemble(parent, next_record, 'synthetic-time')
    assert assembled.revision['summary_sources'] == inherited
    assert '[Source 1](#summary-source-1-1)' in assembled.markdown_content
