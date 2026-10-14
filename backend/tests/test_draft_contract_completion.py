"""Separate development regressions for qualification and summary contracts."""
import pytest
from app.services.evidence_drafting import audit_findings
from evidence_draft_samples import sample_claim, TEXT
from test_evidence_drafting import run


def audit(consistent=True, reviews=None):
    return {'audit_protocol':'target_reviews_v1','summary_consistent':consistent, 'summary_assessment':{'outcome':'consistent' if consistent else 'contradicted','detail':'Synthetic source comparison.','evidence_ids':['episode:one']},
        'paragraph_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic source match.'}],
        'summary_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic source match.'}],
        'document_reviews':[{'document_id':'doc','outcome':'complete','detail':'Synthetic source covered.'}],
        'claim_reviews':reviews}



def reviewed(outcome='supported',evidence=None):
    return [{'claim_id':'claim_01','outcome':outcome,'evidence_ids':['episode:one'] if evidence is None else evidence,
        'detail':'Source records a postponement; no unstated conclusion is inferred.'}]


def test_inconsistent_summary_blocks_even_when_edited(tmp_path):
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit(False,reviewed())})
    assert result['state']=='blocked'
    assert any(f['code']=='summary_inconsistent' for f in result['findings'])


def test_edit_cannot_rewrite_unrelated_summary_clause(tmp_path):
    draft={'paragraphs':[{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}],
        'summary_replacements':[{'old_text':'The hearing is Thursday. Other issues remain open.',
        'new_text':TEXT+' Nothing else needs review.','claim_ids':['claim_01']}]}
    result,_=run(tmp_path,{'EVIDENCE_DRAFT_V1':draft})
    assert result['state']=='blocked'
    assert any(f['code']=='invalid_summary_edits' and f['detail']=='summary_edit_outside_selected_section' for f in result['findings'])


def test_summary_scope_requires_unique_explicit_section_link():
    from app.services.claim_ledger import summary_edit_scope
    assert summary_edit_scope('☀ Selected statement. Protected statement.','Selected statement.')['editable_spans']==[{'start':2,'end':21,'text':'Selected statement.'}]
    assert summary_edit_scope('Different abstract.','Selected statement.')['editable_spans']==[]
    assert summary_edit_scope('Repeated. Repeated.','Repeated.')['editable_spans']==[]


def test_unchanged_edit_with_empty_claims_still_rejected(tmp_path):
    draft={'paragraphs':[{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}],
        'summary_replacements':[{'old_text':'Other issues remain open.','new_text':'Other issues remain open.','claim_ids':[]}]}
    result,_=run(tmp_path,{'EVIDENCE_DRAFT_V1':draft})
    assert result['state']=='blocked'


@pytest.mark.parametrize('reviews',[None,[],reviewed(evidence=['invented']),reviewed(evidence=[]),reviewed()+reviewed()])
def test_incomplete_or_invalid_claim_source_reviews_block(tmp_path,reviews):
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit(True,reviews)})
    assert result['state']=='blocked'
    assert any(f['code']=='invalid_claim_grounding' for f in result['findings'])


@pytest.mark.parametrize('outcome',['unsupported','ambiguous','conflicting','unverified'])
def test_claim_qualification_audit_cannot_be_ignored(tmp_path,outcome):
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit(True,reviewed(outcome))})
    assert result['state']=='blocked'
    assert any(f['code']=='claim_grounding_'+outcome for f in result['findings'])


def test_supported_source_review_and_scoped_patch_can_be_ready(tmp_path):
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit(True,reviewed())})
    assert result['state']=='ready'
    assert result['after']['summary']==TEXT+' Other issues remain open.'


def test_acceptance_rechecks_scoped_summary_even_for_sealed_producer_output(tmp_path,monkeypatch):
    import json
    from evidence_draft_samples import sample_report
    from app.services.report_agent import ReportManager
    from app.services.proposal_store import ProposalStore, ProposalError, proposal_digest
    from app.services.report_revisions import ReportRevisionService
    from test_evidence_drafting import SourceStorage
    monkeypatch.setattr(ReportManager,'REPORTS_DIR',str(tmp_path))
    parent=sample_report();ReportManager.save_report(parent)
    record,_=run(tmp_path)
    assert record['state']=='ready'
    full=parent.outline.summary
    record['summary_edits']=[{'start':0,'end':len(full),'old_text':full,'new_text':TEXT,'claim_ids':['claim_01']}]
    record['after']['summary']=TEXT
    record['proposal_digest']=proposal_digest(record)
    store=ProposalStore(tmp_path)
    store._file(record['proposal_id']).write_text(json.dumps(record))
    with pytest.raises(ProposalError,match='summary_scope_mismatch'):
        ReportRevisionService(store,storage=SourceStorage()).accept(parent.report_id,record['proposal_id'],record['proposal_digest'])
    assert not (tmp_path/record['revision_report_id']).exists()
    assert ReportManager.get_report(parent.report_id).outline.summary==full


def test_server_owned_summary_target_preserves_other_clauses(tmp_path):
    draft={'paragraphs':[{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}],
           'section_summary':{'text':TEXT,'claim_ids':['claim_01']}}
    result,_=run(tmp_path,{'EVIDENCE_DRAFT_V1':draft})
    assert result['state']=='ready'
    assert result['after']['summary']==TEXT+' Other issues remain open.'


def test_competing_summary_contracts_block(tmp_path):
    draft={'paragraphs':[{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}],
           'section_summary':{'text':TEXT,'claim_ids':['claim_01']},'summary_replacements':[]}
    result,_=run(tmp_path,{'EVIDENCE_DRAFT_V1':draft})
    assert result['state']=='blocked'


@pytest.mark.parametrize('consistent',[True,False])
def test_explicit_result_summary_audit(tmp_path,consistent):
    value=audit(consistent,reviewed())
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':value})
    assert result['state']==('ready' if consistent else 'blocked')
    if not consistent:assert any(f['code']=='summary_inconsistent' for f in result['findings'])


def test_conflicting_summary_audit_aliases_block(tmp_path):
    value=audit(True,reviewed());value['summary_unchanged_consistent']=False
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':value})
    assert result['state']=='blocked'


def test_topic_query_retrieves_scoped_original_with_generic_title_suffix():
    from app.services.evidence_drafting import draft_queries
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    from app.utils.draft_budget import DraftBudget
    from evidence_draft_samples import SCOPE
    rows=[{**SCOPE,'uuid':'fence','document_id':'brief','data':'Reservoir fencing design remains pending.'},
          {**SCOPE,'case_id':'foreign','uuid':'other','document_id':'foreign','data':'Reservoir fencing proposal approved.'}]
    corpus=freeze_sources(rows,SCOPE)
    section={'title':'Reservoir fencing proposal','description':'','content':'Old assertion.'}
    assert retrieve_sources(corpus,[section['title']],budget=DraftBudget())['sources']==[]
    selected=retrieve_sources(corpus,draft_queries(section),budget=DraftBudget())['sources']
    assert [source['evidence_id'] for source in selected]==['episode:fence']
