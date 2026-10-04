"""Separate development regressions for qualification and summary contracts."""
import pytest
from app.services.evidence_drafting import audit_findings
from evidence_draft_samples import sample_claim, TEXT
from test_evidence_drafting import run


def audit(consistent=True, reviews=None):
    value={'findings':[],'covered_paragraph_indices':[0],'covered_summary_edit_indices':[0],
        'summary_unchanged_consistent':consistent}
    if reviews is not None:value['claim_reviews']=reviews
    return value


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
