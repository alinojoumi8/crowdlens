"""Scope gaps and AI factual judgments are independent, provider-free gates."""
import copy
import json
import pytest
from evidence_draft_samples import TEXT, sample_report
from test_evidence_drafting import run
from test_proposal_output_reliability import explicit_audit
from test_report_revisions import root
from app.services.proposal_store import ProposalError, ProposalStore, proposal_digest


def assessment(outcome):
    return {'outcome':outcome, 'detail':{'consistent':'Summary matches the source.',
        'contradicted':'Summary says Thursday; source attributes postponement to Alex.',
        'unverified':'Cannot attribute the abstract summary to this selected section.'}[outcome],
        'evidence_ids':['episode:one'] if outcome != 'unverified' else []}


def unmapped(tmp_path, monkeypatch, outcome):
    parent = sample_report()
    parent.outline.summary = 'A broader abstract without a literal section match.'
    monkeypatch.setattr('test_evidence_drafting.sample_report', lambda: parent)
    audit = explicit_audit()
    audit.update(summary_reviews=[], summary_consistent=outcome=='consistent', summary_assessment=assessment(outcome))
    draft = {'paragraphs':[{'text':TEXT, 'kind':'attributed_allegation', 'claim_ids':['claim_01']}],
             'section_summary_claim_ids':None}
    result, llm = run(tmp_path, {'EVIDENCE_DRAFT_V1':draft, 'EVIDENCE_AUDIT_V1':audit})
    return result, llm, parent


@pytest.mark.parametrize('outcome', ['consistent','contradicted','unverified'])
def test_unmapped_scope_blocks_independently_and_retains_judgment(tmp_path, monkeypatch, outcome):
    result, llm, parent = unmapped(tmp_path, monkeypatch, outcome)
    assert result['state'] == 'blocked' and len(llm.calls) == 3
    assert result['before']['summary'] == result['after']['summary'] == parent.outline.summary
    assert result['summary_edits'] == []
    codes = {f['code'] for f in result['findings']}
    assert 'summary_scope_unmapped' in codes
    assert ('summary_inconsistent' in codes) == (outcome=='contradicted')
    assert ('summary_unverified' in codes) == (outcome=='unverified')
    assert result['summary_assessment'] == assessment(outcome)
    scope = next(f for f in result['findings'] if f['code']=='summary_scope_unmapped')
    assert scope['blocking'] and scope['next_action'] and 'does not establish a factual contradiction' in scope['detail']
    saved = llm.store.load_snapshot(result['proposal_id'], 'diagnostics', result['diagnostics_digest'])
    assert saved['auditing']['parsed_response']['summary_assessment'] == assessment(outcome)


@pytest.mark.parametrize('value', [None, {}, {'outcome':'contradicted','detail':'Mismatch','evidence_ids':[]},
    {'outcome':'consistent','detail':'','evidence_ids':[]},
    {'outcome':'contradicted','detail':'Mismatch','evidence_ids':['invented']}])
def test_missing_or_invalid_new_assessment_blocks(tmp_path, value):
    audit = explicit_audit(); audit['summary_assessment']=value
    result, llm = run(tmp_path, {'EVIDENCE_AUDIT_V1':audit})
    assert result['state']=='blocked' and len(llm.calls)==4
    assert any(f.get('field')=='summary_assessment' for f in result['findings'])


def test_assessment_is_digest_bound_and_immutable_without_changing_old_digests(tmp_path):
    result, llm = run(tmp_path)
    changed = copy.deepcopy(result); changed['summary_assessment']['detail']='Tampered rationale'
    assert proposal_digest(changed) != result['proposal_digest']
    with pytest.raises(ProposalError, match='immutable_proposal'):
        llm.store.update(result['proposal_id'], {'ready'}, {'summary_assessment':assessment('unverified')})
    old = {**result, 'policy':'evidence-draft-v13-explicit-audit-targets'}
    old_digest = proposal_digest(old); old.pop('summary_assessment')
    assert proposal_digest(old)==old_digest


def test_accept_recomputes_scope_even_with_digest_consistent_ready_record(root, monkeypatch):
    from app.services.report_agent import ReportManager
    from app.services.report_revisions import ReportRevisionService
    from test_evidence_drafting import SourceStorage
    result, llm, parent = unmapped(root, monkeypatch, 'consistent')
    ReportManager.save_report(parent)
    original = {p.name:p.read_bytes() for p in (root/'report_root').iterdir()}
    result.update(state='ready', findings=[])
    result['proposal_digest']=proposal_digest(result)
    llm.store._file(result['proposal_id'],'record').write_text(json.dumps(result))
    service=ReportRevisionService(ProposalStore(root),storage=SourceStorage())
    with pytest.raises(ProposalError,match='summary_scope_unmapped'):
        service.accept('report_root',result['proposal_id'],result['proposal_digest'])
    assert not (root/result['revision_report_id']).exists()
    assert {p.name:p.read_bytes() for p in (root/'report_root').iterdir()}==original


@pytest.mark.parametrize('outcome,state,code', [('consistent','ready',None),
    ('contradicted','blocked','summary_inconsistent'), ('unverified','blocked','summary_unverified')])
def test_mapped_judgment_has_distinct_outcome(tmp_path, outcome, state, code):
    audit=explicit_audit();audit.update(summary_assessment=assessment(outcome), summary_consistent=outcome=='consistent')
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit})
    assert result['state']==state
    assert 'summary_scope_unmapped' not in {f['code'] for f in result['findings']}
    assert not code or code in {f['code'] for f in result['findings']}


@pytest.mark.parametrize('outcome', [[], {}])
def test_non_string_assessment_is_structural_error(tmp_path, outcome):
    audit=explicit_audit();audit['summary_assessment']['outcome']=outcome
    result,llm=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit})
    assert result['state']=='blocked' and len(llm.calls)==4
    assert result['findings'][0]['field']=='summary_assessment'


def test_structural_retry_cannot_erase_adverse_assessment(tmp_path,monkeypatch):
    from test_evidence_drafting import FakeLLM
    original=FakeLLM.chat_json; audits=[]
    def respond(self,messages,**kwargs):
        result=original(self,messages,**kwargs)
        if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
            result=copy.deepcopy(result);audits.append(result)
            result['summary_consistent']=False
            result['summary_assessment']=assessment('contradicted' if len(audits)==1 else 'unverified')
            if len(audits)==1:result['paragraph_reviews']=[]
        return result
    monkeypatch.setattr(FakeLLM,'chat_json',respond)
    result,_=run(tmp_path)
    assert len(audits)==2 and result['state']=='blocked'
    assert 'audit_adverse_judgment_changed' in {f['code'] for f in result['findings']}


@pytest.mark.parametrize('value', [None, assessment('contradicted'), assessment('unverified')])
def test_accept_rechecks_assessment_even_if_findings_are_removed(root, value):
    from test_report_revisions import ready
    result, service = ready(root)
    result['summary_assessment']=value
    result['proposal_digest']=proposal_digest(result)
    service.store._file(result['proposal_id'],'record').write_text(json.dumps(result))
    with pytest.raises(ProposalError,match='summary_assessment_unverified'):
        service.accept('report_root',result['proposal_id'],result['proposal_digest'])
    assert not (root/result['revision_report_id']).exists()
