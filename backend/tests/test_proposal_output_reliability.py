"""Development regressions: counted JSON recovery and server-built summary prose."""
import json
import pytest
from evidence_draft_samples import TEXT, sample_claim
from test_evidence_drafting import run, FakeLLM


def test_summary_selected_claims_cannot_duplicate_protected_prose(tmp_path):
    draft={'paragraphs':[{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}],
           'section_summary_claim_ids':['claim_01']}
    result,_=run(tmp_path,{'EVIDENCE_DRAFT_V1':draft})
    assert result['state']=='ready'
    assert result['after']['summary']==TEXT+' Other issues remain open.'


@pytest.mark.parametrize('ids',[[],['unknown'],['claim_01','claim_01'],'claim_01'])
def test_invalid_summary_selection_blocks(tmp_path,ids):
    draft={'paragraphs':[{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}],
           'section_summary_claim_ids':ids}
    result,_=run(tmp_path,{'EVIDENCE_DRAFT_V1':draft})
    assert result['state']=='blocked'


def test_malformed_json_receives_one_counted_repair_and_keeps_original(tmp_path,monkeypatch):
    original=FakeLLM.chat_json
    calls=[]
    def respond(self,messages,**kw):
        phase=messages[0]['content'].splitlines()[0];calls.append(phase)
        kw['usage_callback']('synthetic','synthetic',{'input_tokens':1,'output_tokens':1},1)
        if len(calls)==1:
            kw['response_callback']('{"claims":[')
            raise ValueError('invalid_llm_json')
        value=original(self,messages,**kw)
        kw['response_callback'](json.dumps(value))
        return value
    monkeypatch.setattr(FakeLLM,'chat_json',respond)
    result,_=run(tmp_path)
    assert result['state']=='ready'
    assert len(calls)==4 and len(result['usage']['calls'])==4
    from app.services.proposal_store import ProposalStore
    diagnostics=ProposalStore(tmp_path).load_snapshot(result['proposal_id'],'diagnostics',result['diagnostics_digest'])
    assert diagnostics['planning']['attempts'][0]['raw_completion_text']=='{"claims":['
    assert diagnostics['planning']['attempts'][0]['parse_error']=='invalid_llm_json'
    assert diagnostics['planning']['attempts'][1]['repair_of_attempt']==0


def test_repair_exhaustion_blocks_without_third_attempt(tmp_path,monkeypatch):
    calls=[]
    def respond(self,messages,**kw):
        calls.append(messages)
        kw['response_callback']('{broken')
        raise ValueError('invalid_llm_json')
    monkeypatch.setattr(FakeLLM,'chat_json',respond)
    result,_=run(tmp_path)
    assert result['state']=='blocked' and len(calls)==2


def test_summary_audit_contract_excludes_protected_context():
    from app.services.evidence_drafting import summary_review_contract
    before={'summary':'Old hearing. Roof remains pending.','summary_scope_contract':{'editable_spans':[{'start':0,'end':12,'text':'Old hearing.'}]}}
    contract=summary_review_contract(before,[{'start':0,'end':12,'new_text':TEXT,'claim_ids':['claim_01']}])
    assert contract['selected_text']==TEXT and contract['claim_ids']==['claim_01']


def test_non_json_contract_error_is_not_retried(tmp_path,monkeypatch):
    calls=[]
    def respond(self,messages,**kw):
        calls.append(messages)
        kw['response_callback']('{}')
        raise ValueError('invalid_model_output')
    monkeypatch.setattr(FakeLLM,'chat_json',respond)
    result,_=run(tmp_path)
    assert result['state']=='blocked' and len(calls)==1


def explicit_audit():
    return {'audit_protocol':'target_reviews_v1','summary_consistent':True,
      'claim_reviews':[{'claim_id':'claim_01','outcome':'supported','evidence_ids':['episode:one'],'detail':'The original states Alex reports postponement.'}],
      'paragraph_reviews':[{'target_index':0,'outcome':'supported','detail':'Attribution matches original.'}],
      'summary_reviews':[{'target_index':0,'outcome':'supported','detail':'The selected summary matches original.'}],
      'document_reviews':[{'document_id':'doc','outcome':'complete','detail':'The section covers the source postponement account.'}]}


def test_successful_target_judgments_are_not_error_findings(tmp_path):
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':explicit_audit()})
    assert result['state']=='ready' and result['findings']==[]


@pytest.mark.parametrize('field',['paragraph_reviews','summary_reviews','document_reviews'])
def test_missing_target_judgments_block(tmp_path,field):
    audit=explicit_audit();audit[field]=[]
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit})
    assert result['state']=='blocked'


@pytest.mark.parametrize('field,outcome',[('paragraph_reviews','unsupported'),('summary_reviews','ambiguous'),('document_reviews','material_omission')])
def test_negative_target_judgments_block(tmp_path,field,outcome):
    audit=explicit_audit();audit[field][0]['outcome']=outcome
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit})
    assert result['state']=='blocked'


def test_competing_error_list_is_never_ignored(tmp_path):
    audit=explicit_audit();audit['findings']=[{'code':'added_fact'}]
    result,_=run(tmp_path,{'EVIDENCE_AUDIT_V1':audit})
    assert result['state']=='blocked'
