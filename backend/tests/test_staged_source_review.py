"""Synthetic contracts only; private validation documents never enter fixtures."""
import copy
import json

import pytest

from evidence_draft_samples import SCOPE, TEXT, sample_report
from scripts.evidence_quality_support import FixtureStorage
from test_source_completeness import generate, row
from test_evidence_drafting import FakeLLM
from app.services.proposal_store import ProposalStore, ProposalError, proposal_digest
from app.utils.draft_budget import DraftBudget


class StagedLLM(FakeLLM):
    def chat_json(self, messages, **kwargs):
        payload = json.loads(messages[1]['content'])
        phase = messages[0]['content'].splitlines()[0]
        if phase == 'SOURCE_BATCH_REVIEW_V1':
            self.calls.append(phase)
            kwargs['usage_callback']('synthetic', self.model, {'input_tokens': 20, 'output_tokens': 10}, 1)
            return {'reviews': [{'window_id': source['window_id'], 'outcome': 'not_material',
                                'detail': 'Synthetic background unrelated to this section.'}
                               for source in payload['sources']]}
        value = super().chat_json(messages, **kwargs)
        if phase == 'EVIDENCE_LEDGER_V1':
            value['source_exclusions'] = [{'evidence_id': source['evidence_id'], 'reason': 'Synthetic background.'}
                                         for source in payload['sources'] if source['evidence_id'] != 'episode:one']
        if phase == 'EVIDENCE_AUDIT_V1':
            value['document_reviews'] = [{'document_id': identifier, 'outcome': 'complete', 'detail': 'Synthetic covered document.'}
                                         for identifier in payload['audit_contract']['reviewed_document_ids']]
        return value


def large_storage():
    return FixtureStorage([row('one')] + [row(f'z{i:03}', 'Background index. ' * 200, index=i+1) for i in range(40)])


def advance(root, record, storage, llm_class=StagedLLM):
    from app.services.evidence_drafting import EvidenceDraftingService
    store = ProposalStore(root)
    queued, lease = store.admit_continuation('report_root', record['proposal_id'], record['proposal_digest'])
    assert lease is not None
    store.update(record['proposal_id'], {'queued'}, {'state': 'running'})
    llm = llm_class(store, record['proposal_id'])
    try:
        result = EvidenceDraftingService(storage, llm, store).generate(record['proposal_id'], sample_report().to_dict(),
            budget=DraftBudget(previous_usage=record.get('usage')))
    finally:
        lease.close()
    return result, llm


def test_large_corpus_waits_for_all_batches_and_preserves_usage(tmp_path):
    result, llm = generate(tmp_path, large_storage(), StagedLLM)
    assert result['state'] == 'review_pending'
    assert not result['source_completeness']['complete']
    assert result['source_review']['batch_count'] > 1
    total = result['source_review']['batch_count']
    for index in range(total):
        old = result
        result, step = advance(tmp_path, result, large_storage())
        assert step.calls == ['SOURCE_BATCH_REVIEW_V1']
        assert len(result['source_review']['completed_batches']) == index + 1
        assert len(result['usage']['calls']) == index + 1
        assert result['state'] == ('ready' if index + 1 == total else 'review_pending')
        replay, lease = ProposalStore(tmp_path).admit_continuation('report_root', result['proposal_id'], old['proposal_digest'])
        assert lease is None and replay['proposal_digest'] == result['proposal_digest']
        assert replay['state'] == result['state']
    assert result['source_completeness']['complete']
    assert result['source_review']['complete']


def test_long_original_is_split_without_losing_any_interval():
    from app.services.source_completeness import freeze_review_sources, source_completeness
    from app.services.staged_source_review import review_batches
    corpus = freeze_review_sources(FixtureStorage([row('one', TEXT + ' Background.' * 10000)]), SCOPE)
    batches = review_batches(corpus)
    assert len(batches) > 1
    assert all(len(b) <= 30 and sum(len(s['window']) for s in b) <= 60000 for b in batches)
    windows = [s for batch in batches for s in batch]
    assert len({s['window_id'] for s in windows}) == len(windows)
    assert source_completeness(corpus, windows)['complete']


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'foreign', 'omission', 'contradiction', 'unverified'])
def test_batch_failures_never_count_as_complete(tmp_path, problem):
    class BadBatch(StagedLLM):
        def chat_json(self, messages, **kwargs):
            value = super().chat_json(messages, **kwargs)
            reviews = value['reviews']
            if problem == 'missing': reviews.pop()
            elif problem == 'duplicate': reviews[-1] = copy.deepcopy(reviews[0])
            elif problem == 'foreign': reviews[-1]['window_id'] = 'unknown'
            else: reviews[-1].update(outcome={'omission': 'material_omission'}.get(problem, problem), detail='Later adverse evidence.')
            return value
    record, _ = generate(tmp_path, large_storage(), StagedLLM)
    result, llm = advance(tmp_path, record, large_storage(), BadBatch)
    assert result['state'] == 'blocked' and len(llm.calls) == 1
    assert not result['source_review']['complete']
    assert not result['source_completeness']['complete']
    assert any(f['blocking'] for f in result['findings'])


def test_changed_source_blocks_continuation_before_model_call(tmp_path):
    record, _ = generate(tmp_path, large_storage(), StagedLLM)
    result, llm = advance(tmp_path, record, FixtureStorage([row('one', 'Changed source.')]))
    assert result['state'] == 'blocked' and not llm.calls
    assert result['findings'][0]['code'] == 'stale_sources'


def test_pending_cannot_be_accepted_or_mutated(tmp_path):
    from app.services.report_revisions import ReportRevisionService
    record, _ = generate(tmp_path, large_storage(), StagedLLM)
    store = ProposalStore(tmp_path)
    with pytest.raises(ProposalError, match='not_acceptible'):
        ReportRevisionService(store, storage=large_storage()).accept('report_root', record['proposal_id'], record['proposal_digest'])
    with pytest.raises(ProposalError, match='immutable_proposal'):
        store.update(record['proposal_id'], {'review_pending'}, {'source_review': {}})


def test_acceptance_recomputes_every_batch_even_if_flags_resealed(tmp_path, monkeypatch):
    from app.services.report_agent import ReportManager
    from app.services.report_revisions import ReportRevisionService
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    ReportManager.save_report(sample_report())
    record, _ = generate(tmp_path, large_storage(), StagedLLM)
    while record['state'] == 'review_pending':
        record, _ = advance(tmp_path, record, large_storage())
    assert record['state'] == 'ready'
    good = copy.deepcopy(record)
    record['source_review']['completed_batches'].pop()
    record['proposal_digest'] = proposal_digest(record)
    store = ProposalStore(tmp_path)
    store._file(record['proposal_id']).write_text(json.dumps(record))
    with pytest.raises(ProposalError, match='source_review_incomplete'):
        ReportRevisionService(store, storage=large_storage()).accept('report_root', record['proposal_id'], record['proposal_digest'])
    assert not (tmp_path / record['revision_report_id']).exists()
    store._file(record['proposal_id']).write_text(json.dumps(good))
    revision = ReportRevisionService(store, storage=large_storage()).accept('report_root', good['proposal_id'], good['proposal_digest'])
    assert revision.report_id == good['revision_report_id']


@pytest.mark.parametrize('tamper', ['target', 'source', 'receipt', 'duplicate', 'complete_flag'])
def test_checkpoint_tampering_is_rejected(tmp_path, tamper):
    from app.services.source_completeness import freeze_review_sources
    from app.services.staged_source_review import checked_progress
    record, _ = generate(tmp_path, large_storage(), StagedLLM)
    record, _ = advance(tmp_path, record, large_storage())
    if tamper == 'target': record['after']['section'] += ' Altered.'
    elif tamper == 'source': record['source_review']['source_digest'] = 'changed'
    elif tamper == 'receipt': record['source_review']['completed_batches'][0]['batch_digest'] = 'changed'
    elif tamper == 'duplicate': record['source_review']['completed_batches'].append(copy.deepcopy(record['source_review']['completed_batches'][0]))
    else: record['source_review']['complete'] = True
    with pytest.raises(ValueError, match='source_review_incomplete'):
        checked_progress(record, freeze_review_sources(large_storage(), SCOPE))


def test_model_change_and_cancellation_cannot_publish_a_batch(tmp_path):
    class ChangedModel(StagedLLM):
        model = 'changed'
    record, _ = generate(tmp_path, large_storage(), StagedLLM)
    result, llm = advance(tmp_path, record, large_storage(), ChangedModel)
    assert result['state'] == 'blocked' and not llm.calls
    assert result['findings'][0]['code'] == 'source_review_model_changed'
    class Cancelled(StagedLLM):
        def chat_json(self, *args, **kwargs):
            value = super().chat_json(*args, **kwargs)
            self.store.reject('report_root', self.identifier)
            return value
    record, _ = generate(tmp_path / 'cancelled', large_storage(), StagedLLM)
    with pytest.raises(ProposalError, match='state_conflict'):
        advance(tmp_path / 'cancelled', record, large_storage(), Cancelled)
    saved = ProposalStore(tmp_path / 'cancelled').read(record['proposal_id'])
    assert saved['state'] == 'rejected' and not saved['source_review']['completed_batches']
    assert len(saved['usage']['calls']) == 1


def test_full_corpus_limit_still_blocks_before_inference(tmp_path):
    result, llm = generate(tmp_path, FixtureStorage([row(str(i), index=i) for i in range(2001)]), StagedLLM)
    assert result['state'] == 'blocked' and not llm.calls
    assert result['source_completeness']['corpus_limited']


def test_continuation_retains_prior_nonblocking_review_findings(tmp_path):
    record, _ = generate(tmp_path, large_storage(), StagedLLM)
    warning = {'code': 'independent_review_needed', 'blocking': False}
    record['findings'] = [warning]
    record['proposal_digest'] = proposal_digest(record)
    ProposalStore(tmp_path)._file(record['proposal_id']).write_text(json.dumps(record))
    while record['state'] == 'review_pending':
        record, _ = advance(tmp_path, record, large_storage())
    assert record['state'] == 'ready' and record['findings'] == [warning]
