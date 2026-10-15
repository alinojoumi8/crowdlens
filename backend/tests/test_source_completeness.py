import copy
import json
from types import SimpleNamespace
import pytest
from evidence_draft_samples import SCOPE, TEXT, sample_report
from test_evidence_drafting import FakeLLM, SourceStorage, run
from scripts.evidence_quality_support import FixtureStorage
from app.services.source_completeness import freeze_review_sources, retrieve_review_sources, source_completeness
from app.services.proposal_store import ProposalStore, ProposalError, proposal_digest
from app.utils.draft_budget import DraftBudget


def row(uid, text=TEXT, doc='doc', index=0):
    return {**SCOPE, 'uuid':uid, 'document_id':doc, 'data':text, 'chunk_index':index}


def generate(tmp_path, storage, llm_class=FakeLLM):
    from app.services.evidence_drafting import EvidenceDraftingService
    store = ProposalStore(tmp_path)
    rec, lease = store.admit('report_root','key','body')
    store.update(rec['proposal_id'], {'queued'}, {'state':'running','scope':SCOPE,'section_index':1})
    llm = llm_class(store, rec['proposal_id'])
    try:
        result = EvidenceDraftingService(storage,llm,store).generate(rec['proposal_id'],sample_report().to_dict(),budget=DraftBudget())
    finally:
        lease.close()
    return result, llm


def test_later_stakeholder_and_population_qualifiers_reach_auditor(tmp_path):
    late = 'Maya objects. The register counts 18 visitors; the second count is 23 people including staff.'
    class Auditor(FakeLLM):
        def chat_json(self, messages, **kwargs):
            result = super().chat_json(messages, **kwargs)
            phase = messages[0]['content'].splitlines()[0]
            context = json.loads(messages[1]['content'])
            if phase == 'EVIDENCE_LEDGER_V1':
                result['source_exclusions'] = [{'evidence_id':'episode:'+i,'reason':'Synthetic incorrect exclusion.'} for i in ('two','three')]
            if phase == 'EVIDENCE_AUDIT_V1':
                assert late in [s['window'] for s in context['sources']]
                result['document_reviews'][0].update(outcome='material_omission', detail='Maya and the distinct 18 visitors / 23 including staff counts are missing.')
            return result
    result, llm = generate(tmp_path,FixtureStorage([row('one'),row('two','Index.',index=1),row('three',late,index=2)]),Auditor)
    assert result['source_completeness']['complete'] and len(llm.calls) == 3
    assert result['state'] == 'blocked' and any(f['code'] == 'document_material_omission' for f in result['findings'])


@pytest.mark.parametrize('text', ['', '  ', None, 123])
def test_empty_or_invalid_original_stops_before_inference(tmp_path, text):
    class Storage(SourceStorage):
        def get_source_chunks(self, **scope): return [row('one'),row('two',text,doc='missing')]
        def get_source_inventory(self, **scope): return [{'document_id':d,'chunk_count':1,'text_length':50} for d in ('doc','missing')]
    result, llm = generate(tmp_path,Storage())
    assert result['state'] == 'blocked' and not llm.calls
    assert result['findings'][0]['code'] == 'source_completeness_unresolved'
    assert result['source_completeness']['rejected_sources'][0]['document_id'] == 'missing'


@pytest.mark.parametrize('mutation', ['missing_document','unknown_count','duplicate_index','missing_inventory'])
def test_independent_inventory_catches_absent_or_unverifiable_sources(tmp_path, mutation):
    class Storage(SourceStorage):
        def get_source_chunks(self, **scope): return [row('one'),row('two',index=0)] if mutation == 'duplicate_index' else [row('one')]
        def get_source_inventory(self, **scope):
            if mutation == 'missing_inventory': return None
            if mutation == 'missing_document': return [{'document_id':d,'chunk_count':1,'text_length':50} for d in ('doc','absent')]
            return [{'document_id':'doc','chunk_count':2 if mutation == 'duplicate_index' else None,'text_length':50,'chunk_indices':[0,1]}]
    result, llm = generate(tmp_path,Storage())
    assert result['state'] == 'blocked' and not llm.calls


def test_caps_disclose_unreviewed_passages_and_block_before_inference(tmp_path):
    result, llm = generate(tmp_path,FixtureStorage([row(f'{i:02}',doc=f'doc{i}') for i in range(31)]))
    assert result['state'] == 'blocked' and not llm.calls
    missing = [d for d in result['source_completeness']['documents'] if not d['complete']]
    assert len(missing) == 1 and missing[0]['chunks'][0]['omitted_characters'] == len(TEXT)


def test_clipped_large_document_has_partial_interval_and_blocks(tmp_path):
    result, llm = generate(tmp_path,FixtureStorage([row('one',TEXT + ' Background.' * 6000)]))
    assert result['state'] == 'blocked' and not llm.calls
    chunk = result['source_completeness']['documents'][0]['chunks'][0]
    assert chunk['covered_intervals'] and chunk['omitted_characters'] > 0


def test_reconstructed_window_only_credits_original_intersections():
    from test_source_retrieval import split_conditional_pdf_rows
    from app.services.source_retrieval import retrieve_sources
    corpus = freeze_review_sources(FixtureStorage(split_conditional_pdf_rows()),SCOPE)
    partial = retrieve_sources(corpus,['Sora repair purchaser testing'],budget=DraftBudget())
    assert any(s.get('reconstruction') for s in partial['sources'])
    coverage = source_completeness(corpus,partial['sources'])
    assert not coverage['complete'] and any(c['omitted_characters'] > 0 for c in coverage['documents'][0]['chunks'])
    full = retrieve_review_sources(corpus,[],budget=DraftBudget())
    assert source_completeness(corpus,full['sources'])['complete']


def test_foreign_and_forged_sources_cannot_satisfy_coverage():
    corpus = freeze_review_sources(FixtureStorage([row('one')]),SCOPE)
    packet = retrieve_review_sources(corpus,[],budget=DraftBudget())['sources']
    packet[0]['document_id'] = 'foreign'
    assert not source_completeness(corpus,packet)['complete']
    assert not source_completeness(corpus,[])['complete']


def test_coverage_digest_immutable_and_legacy_shape_preserved(tmp_path):
    result, _ = run(tmp_path)
    changed = copy.deepcopy(result); changed['source_completeness']['complete'] = False
    assert proposal_digest(changed) != result['proposal_digest']
    with pytest.raises(ProposalError,match='immutable_proposal'):
        ProposalStore(tmp_path).update(result['proposal_id'],{'ready'},{'source_completeness':{}})
    for policy in ('evidence-draft-v13-explicit-audit-targets','evidence-draft-v14-summary-assessment'):
        old = {**result,'policy':policy}
        assert proposal_digest(old) == proposal_digest({**old,'source_completeness':{'arbitrary':True}})


def test_acceptance_recomputes_coverage_even_with_resealed_positive_flag(tmp_path,monkeypatch):
    from app.services.report_agent import ReportManager
    from app.services.report_revisions import ReportRevisionService
    monkeypatch.setattr(ReportManager,'REPORTS_DIR',str(tmp_path)); ReportManager.save_report(sample_report())
    record, _ = run(tmp_path)
    record['sources'][0]['window_end'] -= 1
    record['proposal_digest'] = proposal_digest(record)
    store = ProposalStore(tmp_path); store._file(record['proposal_id'],'record').write_text(json.dumps(record))
    with pytest.raises(ProposalError,match='source_completeness_unresolved'):
        ReportRevisionService(store,storage=SourceStorage()).accept('report_root',record['proposal_id'],record['proposal_digest'])
    assert not (tmp_path / record['revision_report_id']).exists()


def test_production_inventory_uses_exact_version_and_profile_not_episode_counts(monkeypatch):
    from app.storage.neo4j_storage import Neo4jStorage
    from app.models.case import CaseManager
    doc = SimpleNamespace(document_id='doc',filename='record.txt',hash='hash',text_length=56)
    version = SimpleNamespace(version_id='v1',graph_id='g1',documents=[doc],build_profile={'per_document':[{'document_id':'doc','hash':'hash','text_length':56,'chunk_count':2}]})
    monkeypatch.setattr(CaseManager,'get_case',lambda _:SimpleNamespace(versions=[version]))
    storage = Neo4jStorage.__new__(Neo4jStorage)
    inventory = storage.get_source_inventory(**SCOPE)
    assert inventory[0]['chunk_count'] == 2 and inventory[0]['chunk_indices'] == [0,1]
    assert storage.get_source_inventory(**{**SCOPE,'graph_id':'other'}) is None
    version.build_profile = {'per_document':[]}
    assert storage.get_source_inventory(**SCOPE)[0]['chunk_count'] is None
