"""Export actual retained drafts for human review, including blocked proposals."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.collect_source_review_v2 import load_inputs, CORPUS
from scripts.evidence_quality_reviews import export_packets, import_reviews, json_bytes
from app.services.proposal_store import ProposalStore
from app.services.claim_ledger import render_paragraphs


def export_saved(run, destination, corpus=CORPUS):
    if destination.exists():raise ValueError('preserve_previous_review_export')
    result=json.loads((run/'results.json').read_text());rows,manifest=load_inputs(corpus)
    if result['corpus_manifest']!=manifest:raise ValueError('collection_input_identity_mismatch')
    observations=[];states={}
    fixtures={r['id']:r for r in rows}
    for item in result['cases']:
        if not item.get('proposal_id'):continue
        store=ProposalStore(run/item['case_id']/'reports')
        record=store.read(item['proposal_id'])
        if not record.get('diagnostics_digest'):continue
        diagnostic=store.load_snapshot(item['proposal_id'],'diagnostics',record['diagnostics_digest'])
        draft=diagnostic.get('drafting',{}).get('parsed_response')
        if not draft:continue
        # Render actual paragraphs using unchanged production rendering; validation
        # must succeed, but invalid summary patches remain unapplied and visible.
        section=render_paragraphs(draft['paragraphs'],record['ledger'])
        fixture=fixtures[item['case_id']]
        original_sources=[{'evidence_id':'episode:'+s['uuid'],'excerpt':s['data'],
            'source_hash':s['fixture_text_sha256'],'origin':s['origin'],'filename':s.get('filename'),
            'locator':{'page':s['page'],'paragraph':s['paragraph'],'scope':'complete_frozen_original_document'}}
            for s in fixture['sources'] if all(s.get(k)==v for k,v in fixture['scope'].items()) and s['origin']=='source_document']
        observations.append({'case_id':item['case_id'],'sources':original_sources,'claims':record['ledger'],
            'after':{'section':section,'summary':record.get('after',{}).get('summary',record['before']['summary'])},
            'original_comparison_summary':record['before']['summary'],
            'candidate_summary_edits':record.get('summary_edits',draft.get('summary_edits',[])),
            'candidate_summary_replacements':draft.get('summary_replacements',[]),
            'candidate_section_summary':draft.get('section_summary'),
            'candidate_summary_claim_ids':draft.get('section_summary_claim_ids')})
        states[item['case_id']]={'state':item['state'],'finding_codes':item['finding_codes'],
            'candidate_origin':'actual_model_draft_response','summary_origin':'actual_draft_applied_to_comparison' if record.get('after') else 'authored_comparison_input',
            'summary_edits_applied':bool(record.get('after') and record.get('summary_edits')),'complete_original_sources_provided':True,
            'retrieved_source_ids':[s['evidence_id'] for s in record['sources']],'diagnostics_digest':record['diagnostics_digest']}
    outcome=export_packets(destination,rows,observations,namespace=corpus.name+'-drafts',candidate_origin='actual_minimax_draft_response',real_model_output=True)
    mapping=json.loads((destination/'administrator/mapping.json').read_text())
    for item in mapping:item.update(states[item['fixture_id']])
    (destination/'administrator/mapping.json').write_bytes(json_bytes(mapping))
    forms=[json.loads(line) for line in (destination/'reviewer/blank-review-forms.jsonl').read_text().splitlines()]
    (destination/'blank-import-result.json').write_bytes(json_bytes(import_reviews(destination/'reviewer',forms)))
    (destination/'export-receipt.json').write_bytes(json_bytes({'collection_sha256':hashlib.sha256((run/'results.json').read_bytes()).hexdigest(),
        'original_collection_unmodified':True,'packet_count':outcome['packet_count'],'new_model_requests':0,
        'candidate_kind':'actual_drafts_with_recorded_gate_states','independent_human_labels':None}))
    return outcome


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--corpus',type=Path,default=CORPUS)
    a=p.parse_args();print(json.dumps(export_saved(a.run,a.output,a.corpus)))
