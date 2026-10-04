from pathlib import Path
import pytest
from evidence_draft_samples import SCOPE, TEXT, sample_claim, sample_report
from app.services.proposal_store import ProposalStore
from app.utils.draft_budget import DraftBudget


class SourceStorage:
    def get_source_chunks(self, **scope):
        return [{**SCOPE, 'uuid': 'one', 'document_id': 'doc', 'data': TEXT, 'page': 1}]


class FakeLLM:
    model = 'synthetic'
    def __init__(self, store, identifier, change=None):
        self.store, self.identifier, self.calls, self.change = store, identifier, [], change or {}
    def chat_json(self, messages, **kwargs):
        phase = messages[0]['content'].splitlines()[0]
        self.calls.append(phase)
        if phase == 'EVIDENCE_LEDGER_V1':
            value = {'claims': [sample_claim()], 'gaps': []}
        elif phase == 'EVIDENCE_DRAFT_V1':
            assert self.store._file(self.identifier, 'ledger').exists()
            assert self.store.read(self.identifier)['ledger']
            value = {'paragraphs': [{'text': TEXT, 'kind': 'attributed_allegation', 'claim_ids': ['claim_01']}],
                'summary_edits': [{'start': 0, 'end': 24, 'old_text': 'The hearing is Thursday.',
                    'new_text': TEXT, 'claim_ids': ['claim_01']}]}
        else:
            value = {'findings': [], 'covered_paragraph_indices': [0], 'covered_summary_edit_indices': [0],
                     'summary_unchanged_consistent': True,
                     'claim_reviews': [{'claim_id': 'claim_01', 'outcome': 'supported', 'evidence_ids': ['episode:one'],
                                        'detail': 'The cited source expressly records the postponement.'}]}
        return self.change.get(phase, value)


def run(tmp_path, change=None):
    from app.services.evidence_drafting import EvidenceDraftingService
    store = ProposalStore(tmp_path)
    parent = sample_report().to_dict()
    record, lease = store.admit('report_root', 'key', 'body')
    store.update(record['proposal_id'], {'queued'}, {'state': 'running', 'scope': SCOPE, 'section_index': 1})
    llm = FakeLLM(store, record['proposal_id'], change)
    try:
        result = EvidenceDraftingService(SourceStorage(), llm, store).generate(record['proposal_id'], parent, budget=DraftBudget())
    finally:
        lease.close()
    return result, llm


def test_ledger_before_prose_and_summary_preservation(tmp_path):
    result, llm = run(tmp_path)
    assert result['state'] == 'ready'
    assert len(llm.calls) == 3
    assert result['after']['summary'] == TEXT + ' Other issues remain open.'
    assert result['proposal_digest'] and result['ledger_digest']
    assert result['ledger'][0]['checks'] == []


@pytest.mark.parametrize('claims', [[], None, [{'claim_id': 'invented'}], [{**sample_claim(), 'citation_ids': ['fake']}]] )
def test_invalid_ledger_never_requests_prose(tmp_path, claims):
    result, llm = run(tmp_path, {'EVIDENCE_LEDGER_V1': {'claims': claims}})
    assert result['state'] == 'blocked'
    assert len(llm.calls) == 1


def test_short_section_rejects_oversized_ledger_before_drafting(tmp_path):
    claims = [{**sample_claim(), 'claim_id': f'claim_{index:02}'} for index in range(1, 7)]
    result, llm = run(tmp_path, {'EVIDENCE_LEDGER_V1': {'claims': claims, 'gaps': []}})
    assert result['state'] == 'blocked'
    assert [finding['code'] for finding in result['findings']] == ['invalid_ledger']
    assert llm.calls == ['EVIDENCE_LEDGER_V1']


@pytest.mark.parametrize('audit', [{}, {'findings': [], 'covered_paragraph_indices': [],
    'covered_summary_edit_indices': [0], 'summary_unchanged_consistent': True},
    {'findings': [{'code': 'added_fact', 'target_kind': 'paragraph', 'target_index': 0,
                  'claim_ids': ['claim_01'], 'detail': 'Added fact absent from ledger.'}],
     'covered_paragraph_indices': [0], 'covered_summary_edit_indices': [0], 'summary_unchanged_consistent': True}])
def test_audit_blocks_uncovered_or_new_assertions(tmp_path, audit):
    result, _ = run(tmp_path, {'EVIDENCE_AUDIT_V1': audit})
    assert result['state'] == 'blocked'


def test_scope_crosscheck():
    from app.services.evidence_drafting import source_scope
    assert source_scope(sample_report().to_dict(), {}) == SCOPE
    with pytest.raises(ValueError, match='scope_mismatch'):
        source_scope(sample_report().to_dict(), {'case_id': 'foreign'})


def test_unchanged_inconsistent_summary_blocks(tmp_path):
    draft = {'paragraphs': [{'text': TEXT, 'kind': 'attributed_allegation', 'claim_ids': ['claim_01']}], 'summary_edits': []}
    audit = {'findings': [], 'covered_paragraph_indices': [0], 'covered_summary_edit_indices': [],
             'summary_unchanged_consistent': False}
    result, _ = run(tmp_path, {'EVIDENCE_DRAFT_V1': draft, 'EVIDENCE_AUDIT_V1': audit})
    assert result['state'] == 'blocked'
    assert any(f['code'] == 'summary_inconsistent' for f in result['findings'])


def test_analysis_cannot_attach_invented_citation(tmp_path):
    claim = {**sample_claim(), 'claim_id': 'claim_02', 'kind': 'analysis', 'citation_ids': ['invented'],
             'premise_claim_ids': ['claim_01']}
    result, llm = run(tmp_path, {'EVIDENCE_LEDGER_V1': {'claims': [sample_claim(), claim]}})
    assert result['state'] == 'blocked'
    assert len(llm.calls) == 1


def test_verifier_records_late_usage_before_deadline_fence():
    from types import SimpleNamespace
    from app.services.evidence_drafting import BudgetedRunner
    from app.utils.draft_budget import DeadlineExceeded
    clock = [0]
    budget = DraftBudget(seconds=1, clock=lambda: clock[0])
    class Runner:
        def evaluate(self, **kwargs):
            clock[0] = 2
            return SimpleNamespace(cache_hit=False, model='synthetic', usage={'input_tokens': 5}, elapsed_ms=2000)
    with pytest.raises(DeadlineExceeded):
        BudgetedRunner(Runner(), budget, budget.check).evaluate()
    assert budget.snapshot()['calls'][0]['input_tokens'] == 5
