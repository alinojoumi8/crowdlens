"""Regressions for the missing evidence behind the real blocked proposals.

Original audit/draft responses were not retained. These controlled responses
reproduce their failure mechanisms, without pretending to recover lost text.
"""
import json

import pytest

from evidence_draft_samples import TEXT
from test_evidence_drafting import run


def diagnostics(tmp_path, result):
    path = tmp_path / '.evidence-proposals' / result['proposal_id'] / 'diagnostics.json'
    assert path.exists(), 'Model responses must survive a blocked proposal'
    assert path.stat().st_mode & 0o777 == 0o600
    return json.loads(path.read_text())


def test_invalid_audit_retains_response_and_exact_field(tmp_path):
    from test_proposal_output_reliability import explicit_audit
    audit = explicit_audit();audit['summary_consistent']='true'
    result, llm = run(tmp_path, {'EVIDENCE_AUDIT_V1': audit})
    assert result['state'] == 'blocked' and len(llm.calls) == 3
    finding = result['findings'][0]
    assert finding['code'] == 'invalid_audit'
    assert finding['field'] == 'summary_consistent'
    assert finding['expected'] == 'boolean'
    saved = diagnostics(tmp_path, result)
    assert saved['auditing']['parsed_response'] == audit
    assert result['diagnostics_digest']


def test_missing_summary_target_stays_blocked_with_precise_reason(tmp_path):
    draft = {'paragraphs': [{'text': TEXT, 'kind': 'attributed_allegation',
                            'claim_ids': ['claim_01']}], 'summary_edits': []}
    audit = {'findings': [{'code': 'summary_inconsistent', 'target_kind': 'summary_edit',
                          'target_index': 0, 'claim_ids': ['claim_01'], 'detail': 'Changed summary'}],
             'covered_paragraph_indices': [0], 'covered_summary_edit_indices': [],
             'summary_unchanged_consistent': False}
    result, _ = run(tmp_path, {'EVIDENCE_DRAFT_V1': draft, 'EVIDENCE_AUDIT_V1': audit})
    assert result['state'] == 'blocked'
    assert result['findings'][0]['field'] == 'audit_protocol'
    assert diagnostics(tmp_path, result)['auditing']['parsed_response'] == audit


def test_mixed_kinds_keep_both_indices_and_draft_for_reproduction(tmp_path):
    paragraphs = [{'text': TEXT, 'kind': 'source_statement' if i in (0, 7) else 'attributed_allegation',
                   'claim_ids': ['claim_01']} for i in range(8)]
    draft = {'paragraphs': paragraphs, 'summary_edits': []}
    result, llm = run(tmp_path, {'EVIDENCE_DRAFT_V1': draft})
    assert result['state'] == 'blocked' and len(llm.calls) == 2
    mismatches = [f for f in result['findings'] if f['code'] == 'paragraph_kind_mismatch']
    assert [f['paragraph_index'] for f in mismatches] == [0, 7]
    assert all(f['expected_kinds'] == ['attributed_allegation'] for f in mismatches)
    assert diagnostics(tmp_path, result)['drafting']['parsed_response'] == draft


def test_exact_contract_is_sent_to_draft_and_audit(tmp_path, monkeypatch):
    from test_evidence_drafting import FakeLLM
    original = FakeLLM.chat_json
    payloads = {}
    def record(self, messages, **kwargs):
        payloads[messages[0]['content'].splitlines()[0]] = json.loads(messages[1]['content'])
        return original(self, messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', record)
    result, _ = run(tmp_path)
    assert result['state'] == 'ready'
    assert payloads['EVIDENCE_DRAFT_V1']['claim_kind_contract'] == {'claim_01': 'attributed_allegation'}
    contract = payloads['EVIDENCE_AUDIT_V1']['audit_contract']
    assert contract['covered_paragraph_indices'] == [0]
    assert contract['covered_summary_edit_indices'] == [0]
    assert contract['valid_claim_ids'] == ['claim_01']


@pytest.mark.parametrize('raw', ['```json\n{"ok":true}\n```', '{broken json'])
def test_completion_observer_runs_before_json_parsing(raw):
    from app.utils.llm_client import LLMClient
    client = object.__new__(LLMClient)
    calls, captured = [], []
    client.chat = lambda **kwargs: calls.append(kwargs) or raw
    if raw.startswith('{broken'):
        with pytest.raises(ValueError, match='invalid_llm_json'):
            client.chat_json([], response_callback=captured.append)
    else:
        assert client.chat_json([], response_callback=captured.append) == {'ok': True}
    assert calls and len(calls) == 1
    assert captured == [raw]


def test_malformed_oversized_completion_is_retained_privately_through_service(tmp_path, monkeypatch):
    from app.utils.llm_client import LLMClient
    from test_evidence_drafting import FakeLLM
    import hashlib
    raw = '{broken ' + 'x' * 256000
    def malformed(self, messages, **kwargs):
        client = object.__new__(LLMClient)
        client.chat = lambda **kw: raw
        return client.chat_json(messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', malformed)
    result, _ = run(tmp_path)
    assert result['state'] == 'blocked'
    saved = diagnostics(tmp_path, result)['planning']
    assert len(saved['raw_completion_text']) == 256000
    assert saved['raw_truncated'] is True
    assert saved['raw_sha256'] == hashlib.sha256(raw.encode()).hexdigest()
    assert saved['parse_error'] == 'invalid_json_or_model_output'


def test_late_raw_callback_cannot_revive_rejected_proposal(tmp_path, monkeypatch):
    from test_evidence_drafting import FakeLLM
    from app.services.proposal_store import ProposalError
    def late(self, messages, **kwargs):
        self.store.update(self.identifier, {'running'}, {'state': 'rejected'})
        kwargs['response_callback']('{"claims":[]}')
        return {'claims': []}
    monkeypatch.setattr(FakeLLM, 'chat_json', late)
    with pytest.raises(ProposalError, match='state_conflict'):
        run(tmp_path)
    record = json.loads(next((tmp_path / '.evidence-proposals').glob('*/record.json')).read_text())
    assert record['state'] == 'rejected' and not record.get('after')
