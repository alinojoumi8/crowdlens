"""Structural checks only; frozen held-out claims are never quality-labelled here."""
import json
from scripts.collect_source_review_v2 import load_inputs
from scripts.evidence_quality_reviews import export_packets, import_reviews


def test_frozen_inputs_are_separate_and_hash_valid():
    rows,manifest=load_inputs()
    assert len(rows)==4 and len({r['scope']['case_id'] for r in rows})==4
    assert manifest['independent_quality_labels'] is None
    assert all('stub_claims' not in r and r['split']=='holdout' for r in rows)


def test_real_output_export_does_not_leak_identity_or_invent_human_labels(tmp_path):
    # Synthetic test response tests export only, never included in collected results.
    rows,_=load_inputs();r=rows[0];s=r['sources'][0]
    observations=[{'case_id':r['id'],'sources':[{'evidence_id':'episode:'+s['uuid'],'excerpt':s['data'],'source_hash':s['fixture_text_sha256'],'origin':'source_document','locator':{}}],
        'claims':[{'claim_id':'claim_01','kind':'analysis','text':'Synthetic exporter test only','premise_claim_ids':['test_premise']}],
        'after':{'section':'Synthetic exporter test only','summary':''}}]
    export_packets(tmp_path,[r],observations,namespace='source-review-v2',candidate_origin='actual_minimax_proposal',real_model_output=True)
    packet=json.loads(next((tmp_path/'reviewer').glob('packet_*.json')).read_text())
    assert not {'model','expected','findings','candidate_origin'} & set(packet)
    mapping=json.loads((tmp_path/'administrator/mapping.json').read_text())[0]
    assert mapping['real_model_output'] is True
    forms=[json.loads(x) for x in (tmp_path/'reviewer/blank-review-forms.jsonl').read_text().splitlines()]
    result=import_reviews(tmp_path/'reviewer',forms)
    assert result['status']=='PENDING' and result['reviewed_packets']==0
    assert result['unsupported_claims_per_review']['rate'] is None
    assert result['measured_review_seconds']['total'] is None


def test_workflow_halt_retains_all_planned_cases_and_null_reviews(tmp_path, monkeypatch):
    from app.config import Config
    from app.services.workflow_execution import WorkflowHalt
    from scripts.collect_source_review_v2 import collect
    class HaltedClient:
        def chat_json(self, *args, **kwargs):
            raise WorkflowHalt('request_limit')
    monkeypatch.setattr(Config,'LLM_DEFAULT_PROVIDER','minimax')
    monkeypatch.setattr(Config,'LLM_MODEL_NAME','MiniMax-M3')
    monkeypatch.setattr(Config,'JEV_EVIDENCE_MODE','off')
    monkeypatch.setattr('app.utils.llm_client.LLMClient',HaltedClient)
    result=collect(tmp_path/'halted')
    assert len(result['cases'])==4
    assert result['cases'][0]['state']=='failed'
    assert all(c['state']=='not_attempted' for c in result['cases'][1:])
    assert result['ready_rate']=={'numerator':0,'denominator':4}
    assert result['attempted_cases']==1
    assert result['workflow']['state']=='stopped'


def test_prose_citation_numbers_preserve_ledger_order_not_retrieval_order(tmp_path):
    rows,_=load_inputs();r=rows[0]
    sources=[{'evidence_id':'episode:'+s['uuid'],'excerpt':s['data'],'source_hash':s['fixture_text_sha256'],'origin':'source_document','locator':{}} for s in r['sources'][:2]]
    claims=[{'claim_id':'claim_01','text':'Test B','kind':'source_statement','citation_ids':[sources[1]['evidence_id']]},
            {'claim_id':'claim_02','text':'Test A','kind':'source_statement','citation_ids':[sources[0]['evidence_id']]}]
    export_packets(tmp_path,[r],[{'case_id':r['id'],'sources':sources,'claims':claims,'after':{'section':'Test B [1]. Test A [2].','summary':''}}])
    packet=json.loads(next((tmp_path/'reviewer').glob('packet_*.json')).read_text())
    assert packet['citation_number_sources']=={'1':'S02','2':'S01'}


def test_review_ui_preserves_literal_text_without_script_injection(tmp_path):
    import re
    from scripts.build_source_review_ui import build
    packet={'packet_id':'packet_test','sources':[],'claims':[],'candidate_section':'<script>not markup</script> & < 5'}
    (tmp_path/'packet_test.json').write_text(json.dumps(packet))
    (tmp_path/'blank-review-forms.jsonl').write_text(json.dumps({'packet_id':'packet_test'})+'\n')
    build(tmp_path)
    page=(tmp_path/'index.html').read_text()
    embedded=re.search(r'const DATA=(.*);\nconst \$',page).group(1)
    assert json.loads(embedded)['packets'][0]['candidate_section']==packet['candidate_section']
    assert '<script>not markup' not in page
