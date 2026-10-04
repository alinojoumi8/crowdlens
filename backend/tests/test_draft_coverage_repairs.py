"""Development regressions; do not tune on retained v2 held-out outputs."""
import json
import pytest
from app.utils.draft_budget import DraftBudget
from app.services.source_retrieval import freeze_sources, retrieve_sources
from evidence_draft_samples import SCOPE, TEXT, sample_claim
from test_evidence_drafting import run, FakeLLM


def source(identifier, document, text, **changes):
    return {**SCOPE, 'uuid':identifier,'document_id':document,'data':text,'page':1,**changes}


def test_matching_document_keeps_unmatched_companion_original_and_scope():
    rows=[source('a','agenda','Workshop registration records seven students.'),
          source('b','followup','No invoice has been approved.'),
          source('c','foreign','No invoice has been approved.',case_version_id='old')]
    packet=retrieve_sources(freeze_sources(rows,SCOPE),['Workshop registration'],budget=DraftBudget())
    assert {s['episode_id'] for s in packet['sources']}=={'a','b'}
    assert packet['rankings']['represented_documents']==2
    assert packet['rankings']['admitted_documents']==2


def test_document_coverage_does_not_claim_complete_when_capped():
    rows=[source(str(i),str(i),'Workshop registration '+str(i)) for i in range(35)]
    packet=retrieve_sources(freeze_sources(rows,SCOPE),['Workshop registration'],budget=DraftBudget())
    assert len(packet['sources'])==30
    assert 'document_coverage_truncated' in packet['limitations']
    assert packet['rankings']['represented_documents']==30
    assert packet['rankings']['admitted_documents']==35


def test_exact_summary_replacement_resolves_unicode_and_preserves_other_sections():
    from app.services.claim_ledger import resolve_summary_replacements, apply_summary_edits
    original='☂ Café costs are pending. Separate project unchanged.'
    edits=resolve_summary_replacements(original,[{'old_text':'Café costs are pending.','new_text':'Café costs await approval.','claim_ids':['claim_01']}],[sample_claim()])
    assert edits[0]['start']==2
    assert apply_summary_edits(original,edits,[sample_claim()])=='☂ Café costs await approval. Separate project unchanged.'


@pytest.mark.parametrize('original,old',[('Same. Same.','Same.'),('Summary only.','Section prose absent from summary.'),('Summary only.','')])
def test_summary_replacements_reject_ambiguous_stale_and_empty_targets(original,old):
    from app.services.claim_ledger import resolve_summary_replacements
    with pytest.raises(ValueError):
        resolve_summary_replacements(original,[{'old_text':old,'new_text':'Repair','claim_ids':['claim_01']}],[sample_claim()])


def test_drafting_uses_exact_summary_target_not_model_offsets(tmp_path,monkeypatch):
    original=FakeLLM.chat_json;payloads={}
    def record(self,messages,**kwargs):
        payloads[messages[0]['content'].splitlines()[0]]=json.loads(messages[1]['content'])
        return original(self,messages,**kwargs)
    monkeypatch.setattr(FakeLLM,'chat_json',record)
    draft={'paragraphs':[{'text':TEXT,'kind':'attributed_allegation','claim_ids':['claim_01']}],
           'summary_replacements':[{'old_text':'The hearing is Thursday.','new_text':TEXT,'claim_ids':['claim_01']}]}
    result,_=run(tmp_path,{'EVIDENCE_DRAFT_V1':draft})
    assert result['state']=='ready'
    assert result['after']['summary']==TEXT+' Other issues remain open.'
    assert result['summary_edits'][0]['end']==24
    assert payloads['EVIDENCE_DRAFT_V1']['summary_patch_contract']['target_text']==result['before']['summary']


def test_planned_claim_cannot_disappear_from_draft(tmp_path):
    second={**sample_claim(),'claim_id':'claim_02','text':'Alex describes a postponement.'}
    result,_=run(tmp_path,{'EVIDENCE_LEDGER_V1':{'claims':[sample_claim(),second],'gaps':[]}})
    assert result['state']=='blocked'
    assert any(f['code']=='undrafted_claim' and f['claim_id']=='claim_02' for f in result['findings'])


def test_review_export_preserves_original_filename_metadata(tmp_path):
    from scripts.evidence_quality_reviews import export_packets
    fixture={'id':'development','human_review_packet':True,'split':'development','section':{'description':'Review source.'}}
    obs={'case_id':'development','sources':[{'evidence_id':'one','filename':'original-notice.txt','origin':'source_document','excerpt':'Notice.','source_hash':'hash','locator':{}}],
         'claims':[],'after':{'section':'Notice.','summary':'Notice.'}}
    export_packets(tmp_path,[fixture],[obs])
    packet=json.loads(next((tmp_path/'reviewer').glob('packet_*.json')).read_text())
    assert packet['sources'][0]['filename']=='original-notice.txt'
