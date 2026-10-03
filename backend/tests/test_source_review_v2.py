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
        'claims':[{'claim_id':'claim_01','kind':'source_statement','text':'Synthetic exporter test only','citation_ids':['episode:'+s['uuid']]}],
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
