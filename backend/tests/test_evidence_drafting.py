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
        assert 0 < kwargs['request_timeout'] <= (90 if phase == 'EVIDENCE_AUDIT_V1' else 60)
        assert kwargs['request_max_retries'] == 0
        if phase == 'EVIDENCE_LEDGER_V1':
            value = {'claims': [sample_claim()], 'gaps': []}
        elif phase == 'EVIDENCE_DRAFT_V1':
            assert self.store._file(self.identifier, 'ledger').exists()
            assert self.store.read(self.identifier)['ledger']
            value = {'paragraphs': [{'text': TEXT, 'kind': 'attributed_allegation', 'claim_ids': ['claim_01']}],
                'summary_edits': [{'start': 0, 'end': 24, 'old_text': 'The hearing is Thursday.',
                    'new_text': TEXT, 'claim_ids': ['claim_01']}]}
        else:
            value = {'audit_protocol':'target_reviews_v1', 'summary_consistent':True,
                     'paragraph_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic matched source.'}],
                     'summary_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic matched source.'}],
                     'document_reviews':[{'document_id':'doc','outcome':'complete','detail':'Synthetic source covered.'}],
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


def test_one_quote_correction_still_requires_the_normal_audit(tmp_path, monkeypatch):
    import json
    original = FakeLLM.chat_json
    count = 0
    def chat(self, messages, **kwargs):
        nonlocal count
        if messages[0]['content'].startswith('EVIDENCE_LEDGER_V1'):
            count += 1
            if count == 1:
                self.calls.append('EVIDENCE_LEDGER_V1')
                return {'claims':[{**sample_claim(), 'quote':'Alex signed an approval.'}], 'gaps':[]}
            assert 'ledger_correction' in json.loads(messages[1]['content'])
        return original(self, messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    result, llm = run(tmp_path)
    assert result['state'] == 'ready' and count == 2
    assert llm.calls == ['EVIDENCE_LEDGER_V1', 'EVIDENCE_LEDGER_V1', 'EVIDENCE_DRAFT_V1', 'EVIDENCE_AUDIT_V1']
    diagnostics = llm.store.load_snapshot(result['proposal_id'], 'diagnostics', result['diagnostics_digest'])
    assert diagnostics['planning']['parsed_response']['claims'][0]['quote'] == 'Alex signed an approval.'


def test_repeated_bad_quote_stops_before_drafting(tmp_path):
    result, llm = run(tmp_path, {'EVIDENCE_LEDGER_V1': {'claims':[{**sample_claim(), 'quote':'Invented approval.'}], 'gaps':[]}})
    assert result['state'] == 'blocked' and len(llm.calls) == 2
    assert any(f['code'] == 'quote_absent' for f in result['findings'])


def test_missing_claim_is_materialized_and_still_audited(tmp_path, monkeypatch):
    import json
    original = FakeLLM.chat_json
    second = {**sample_claim(), 'claim_id': 'claim_02'}
    def chat(self, messages, **kwargs):
        phase = messages[0]['content'].splitlines()[0]
        if phase == 'EVIDENCE_AUDIT_V1':
            context = json.loads(messages[1]['content'])
            assert context['paragraphs'][1] == {'text': second['text'], 'kind': second['kind'], 'claim_ids': ['claim_02']}
            result = original(self, messages, **kwargs)
            result['claim_reviews'].append({'claim_id':'claim_02', 'outcome':'unsupported', 'evidence_ids':['episode:one'], 'detail':'Synthetic adverse review must remain blocking.'})
            result['paragraph_reviews'].append({'target_index':1,'outcome':'unsupported','detail':'Synthetic adverse review.'})
            return result
        return original(self, messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    result, llm = run(tmp_path, {'EVIDENCE_LEDGER_V1': {'claims':[sample_claim(), second], 'gaps':[]}})
    assert result['state'] == 'blocked'
    assert len(llm.calls) == 3
    assert not any(f['code'] == 'undrafted_claim' for f in result['findings'])
    assert result['extract_provenance']['coverage_resolutions'][0]['claim_id'] == 'claim_02'


@pytest.mark.parametrize('paragraphs', [[], [{'text':TEXT,'kind':'analysis','claim_ids':['claim_01']}], [{'text':TEXT,'kind':'attributed_allegation','claim_ids':['invented']}]])
def test_coverage_never_repairs_invalid_drafts(paragraphs):
    from app.services.claim_coverage import complete_claim_coverage
    assert complete_claim_coverage(paragraphs, [sample_claim()], []) == (paragraphs, [])


def test_coverage_respects_paragraph_limit_and_input_snapshot():
    from app.services.claim_coverage import complete_claim_coverage
    import copy
    paragraphs = [{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}] * 60
    ledger = [sample_claim(), {**sample_claim(), 'claim_id':'claim_02'}]
    assert complete_claim_coverage(paragraphs, ledger, []) == (paragraphs, [])
    original = copy.deepcopy(paragraphs[:1])
    completed, resolutions = complete_claim_coverage(original, ledger, [])
    assert len(original) == 1 and len(completed) == 2 and len(resolutions) == 1


@pytest.mark.parametrize('corrected', [True, False])
def test_unrepresented_window_gets_one_counted_planning_correction(tmp_path, monkeypatch, corrected):
    import json
    monkeypatch.setattr(SourceStorage, 'get_source_chunks', lambda self, **scope: [
        {**SCOPE,'uuid':'one','document_id':'doc','data':TEXT,'page':1},
        {**SCOPE,'uuid':'two','document_id':'doc','data':'Alex states that hearing records include an exhibit index.','page':2}])
    original = FakeLLM.chat_json
    count = 0
    def chat(self, messages, **kwargs):
        nonlocal count
        if messages[0]['content'].startswith('EVIDENCE_LEDGER_V1'):
            count += 1
            if count == 2:
                correction = json.loads(messages[1]['content'])['ledger_correction']
                assert correction['findings'][0]['code'] == 'unaccounted_source_window'
                if corrected:
                    self.calls.append('EVIDENCE_LEDGER_V1')
                    second = {**sample_claim(),'claim_id':'claim_02',
                        'text':'Alex states that hearing records include an exhibit index.', 'citation_ids':['episode:two']}
                    return {'claims':[sample_claim(), second], 'gaps':[]}
        return original(self, messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    result, llm = run(tmp_path)
    assert count == 2
    if corrected:
        assert 'EVIDENCE_AUDIT_V1' in llm.calls
        assert not any(f['code']=='unaccounted_source_window' for f in result['findings'])
    else:
        assert len(llm.calls) == 2 and result['state'] == 'blocked'
        assert result['findings'][0]['code'] == 'unaccounted_source_window'


def test_source_exclusion_is_still_subject_to_document_audit(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(SourceStorage, 'get_source_chunks', lambda self, **scope: [
        {**SCOPE,'uuid':'one','document_id':'doc','data':TEXT,'page':1},
        {**SCOPE,'uuid':'two','document_id':'doc','data':'Hearing record lists required conditions.','page':2}])
    exclusion = {'evidence_id':'episode:two', 'reason':'Planner alleges unrelated material.'}
    original = FakeLLM.chat_json
    def chat(self, messages, **kwargs):
        if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
            assert json.loads(messages[1]['content'])['source_exclusions'] == [exclusion]
        return original(self, messages, **kwargs)
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    audit = {'audit_protocol':'target_reviews_v1','summary_consistent':True,
        'paragraph_reviews':[{'target_index':0,'outcome':'supported','detail':'Source matched.'}],
        'summary_reviews':[{'target_index':0,'outcome':'supported','detail':'Source matched.'}],
        'claim_reviews':[{'claim_id':'claim_01','outcome':'supported','evidence_ids':['episode:one'],'detail':'Source matched.'}],
        'document_reviews':[{'document_id':'doc','outcome':'material_omission','detail':'Excluded required conditions are task-relevant.'}]}
    result, llm = run(tmp_path, {'EVIDENCE_LEDGER_V1':{'claims':[sample_claim()],'gaps':[], 'source_exclusions':[exclusion]}, 'EVIDENCE_AUDIT_V1':audit})
    assert result['state'] == 'blocked' and len(llm.calls) == 3
    assert any(f['code'] == 'document_material_omission' for f in result['findings'])


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
    audit = {'audit_protocol':'target_reviews_v1','summary_consistent':False,
             'paragraph_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic source match.'}],
             'summary_reviews':[], 'document_reviews':[{'document_id':'doc','outcome':'complete','detail':'Source covered.'}],
             'claim_reviews':[{'claim_id':'claim_01','outcome':'supported','evidence_ids':['episode:one'],'detail':'Source match.'}]}
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


def test_invented_summary_target_gets_one_structure_correction(tmp_path, monkeypatch):
    original = FakeLLM.chat_json
    audits = []
    def chat(self, messages, **kwargs):
        import json
        result = original(self, messages, **kwargs)
        if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
            payload = json.loads(messages[1]['content'])
            audits.append(payload)
            if len(audits) == 1:
                result['summary_reviews'].append({'target_index': 1, 'outcome': 'supported', 'detail': 'Invented target'})
            else:
                assert 'audit_structure_correction' in payload
        return result
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    result, llm = run(tmp_path)
    assert result['state'] == 'ready'
    assert len(audits) == 2 and len(llm.calls) == 4


def test_persistently_invalid_audit_stays_blocked_after_one_correction(tmp_path):
    result, llm = run(tmp_path, {'EVIDENCE_AUDIT_V1': {'audit_protocol': 'target_reviews_v1'}})
    assert result['state'] == 'blocked'
    assert llm.calls.count('EVIDENCE_AUDIT_V1') == 2


def test_valid_adverse_audit_is_not_retried(tmp_path, monkeypatch):
    original = FakeLLM.chat_json
    def chat(self, messages, **kwargs):
        result = original(self, messages, **kwargs)
        if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
            result['paragraph_reviews'][0].update(outcome='unsupported', detail='Not supported by source.')
        return result
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    result, llm = run(tmp_path)
    assert result['state'] == 'blocked'
    assert llm.calls.count('EVIDENCE_AUDIT_V1') == 1
    assert any(f['code'] == 'target_unsupported' for f in result['findings'])



def test_structure_correction_cannot_erase_adverse_claim_judgment(tmp_path, monkeypatch):
    original = FakeLLM.chat_json
    count = 0
    def chat(self, messages, **kwargs):
        nonlocal count
        result = original(self, messages, **kwargs)
        if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
            count += 1
            if count == 1:
                result['summary_reviews'] = []
                result['claim_reviews'][0].update(outcome='unsupported', detail='Source contradicts claim.')
        return result
    monkeypatch.setattr(FakeLLM, 'chat_json', chat)
    result, _ = run(tmp_path)
    assert result['state'] == 'blocked' and count == 2
    assert any(f['code'] == 'audit_adverse_judgment_changed' for f in result['findings'])
