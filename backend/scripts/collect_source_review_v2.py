"""Opt-in actual-provider held-out proposal collection; never import human labels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evidence_quality_reviews import export_packets, import_reviews, json_bytes
from scripts.evidence_quality_support import FixtureStorage, artifact_hashes

CORPUS = Path(__file__).resolve().parents[1] / 'evaluations/source-review-v2'


def load_inputs(corpus=CORPUS):
    manifest = json.loads((corpus/'manifest.json').read_text())
    for name, digest in manifest['files_sha256'].items():
        if hashlib.sha256((corpus/name).read_bytes()).hexdigest() != digest:
            raise ValueError('frozen_input_hash_mismatch')
    rows = json.loads((corpus/'cases.json').read_text())['cases']
    for row in rows:
        for source in row['sources']:
            if hashlib.sha256(source['data'].encode()).hexdigest() != source['fixture_text_sha256']:
                raise ValueError('source_hash_mismatch')
    return rows, manifest


def collect(output, corpus=CORPUS, max_requests=12):
    from app.config import Config
    from app.utils.llm_client import LLMClient
    from app.utils.draft_budget import DraftBudget
    from app.services.evidence_drafting import EvidenceDraftingService, LEDGER_PROMPT, DRAFT_PROMPT, AUDIT_PROMPT
    from app.services.proposal_store import ProposalStore
    from app.services.report_agent import ReportManager, Report, ReportStatus, ReportOutline, ReportSection
    from app.services.workflow_execution import WorkflowLedger, WorkflowHalt, execution_scope
    rows, manifest = load_inputs(corpus)
    if output.exists():
        raise ValueError('output_exists_preserve_previous_attempts')
    if Config.LLM_DEFAULT_PROVIDER != 'minimax' or Config.LLM_MODEL_NAME != 'MiniMax-M3':
        raise ValueError('frozen_provider_identity_mismatch')
    if Config.JEV_EVIDENCE_MODE != 'off':
        raise ValueError('extra_grader_disabled_by_protocol')
    output.mkdir(parents=True)
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=CORPUS,text=True).strip()
    result = {'schema_version':1,'code_revision':revision,'corpus_manifest':manifest,
        'provider':Config.LLM_DEFAULT_PROVIDER,'model':Config.LLM_MODEL_NAME,
        'prompt_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in
            [('ledger',LEDGER_PROMPT),('draft',DRAFT_PROMPT),('audit',AUDIT_PROMPT)]},
        'attempts_per_case':1,'real_model_outputs':True,'quality_labels':None,'cost':None,'cases':[]}
    ledger = WorkflowLedger(str(output/'control.db'))
    workflow=ledger.authorize(request_key=corpus.name,provider=Config.LLM_DEFAULT_PROVIDER,
        model=Config.LLM_MODEL_NAME,base_url=Config.LLM_BASE_URL,input_description=f'{len(rows)} frozen fictional {corpus.name} cases; one unchanged proposal attempt each',
        input_fingerprint=manifest['files_sha256']['cases.json'],max_requests=max_requests,max_seconds=900,confirmed=True)
    observations=[]
    halted_reason=None
    try:
        for row in rows:
            directory=output/row['id'];store=ProposalStore(directory/'reports')
            ReportManager.REPORTS_DIR=str(store.root)
            parent=Report('report_'+row['id'],'sim_'+row['id'],row['scope']['graph_id'],'Fictional held-out source review',
                ReportStatus.NEEDS_REVIEW,source_grounding=row['scope'],outline=ReportOutline('Fictional source review',row['summary'],[ReportSection(**row['section'])]))
            ReportManager.save_report(parent)
            before=artifact_hashes(store.root/parent.report_id)
            record,lease=store.admit(parent.report_id,'once_'+row['id'],'frozen-v2')
            store.update(record['proposal_id'],{'queued'},{'state':'running','scope':row['scope'],'section_index':1})
            started=time.monotonic();budget=DraftBudget(seconds=180)
            try:
                with execution_scope(ledger,workflow['workflow_id'],'proposal'):
                    record=EvidenceDraftingService(FixtureStorage(row['sources']),LLMClient(),store).generate(record['proposal_id'],parent.to_dict(),budget=budget)
            except (Exception, WorkflowHalt) as exc:
                if isinstance(exc, WorkflowHalt): halted_reason=exc.reason
                record=store.read(record['proposal_id'])
                if record['state']=='running':record=store.update(record['proposal_id'],{'running'},{'state':'failed','error_code':type(exc).__name__,'usage':budget.snapshot()})
            finally:lease.close()
            unchanged=before==artifact_hashes(store.root/parent.report_id)
            allowed={'episode:'+s['uuid'] for s in row['sources'] if all(s.get(k)==v for k,v in row['scope'].items()) and s['origin']=='source_document'}
            selected={s['evidence_id'] for s in record.get('sources',[])}
            scope_ok=bool(selected) and selected <= allowed
            item={'case_id':row['id'],'state':record['state'],'proposal_id':record['proposal_id'],
                'finding_codes':[f['code'] for f in record.get('findings',[])],'error_code':record.get('error_code'),
                'elapsed_seconds':time.monotonic()-started,'usage':budget.snapshot(),
                'parent_unchanged':unchanged,'original_source_scope_valid':scope_ok,
                'selected_source_ids':sorted(selected),'allowed_source_ids':sorted(allowed)}
            result['cases'].append(item)
            observations.append({'case_id':row['id'],'sources':record.get('sources',[]),
                'claims':record.get('ledger',[]),'after':record.get('after')})
            (output/'results.json').write_bytes(json_bytes(result))
            print(json.dumps({k:item[k] for k in ('case_id','state','finding_codes','parent_unchanged','original_source_scope_valid')}),flush=True)
            if halted_reason: break
    finally:
        result['workflow']=ledger.stop(workflow['workflow_id'])
        attempted={c['case_id'] for c in result['cases']}
        result['attempted_cases']=len(attempted)
        result['cases'].extend({'case_id':r['id'],'state':'not_attempted','error_code':halted_reason or 'collection_interrupted',
            'finding_codes':[],'usage':None,'elapsed_seconds':None,'parent_unchanged':None,'original_source_scope_valid':None}
            for r in rows if r['id'] not in attempted)
        result['ready_rate']={'numerator':sum(c['state']=='ready' for c in result['cases']),'denominator':len(rows)}
        result['collection_complete']=len(attempted)==len(rows)
        (output/'results.json').write_bytes(json_bytes(result))
    result['review_export']=export_packets(output/'human-review',rows,observations,namespace=corpus.name,candidate_origin='actual_minimax_proposal',real_model_output=True)
    reviewer=output/'human-review/reviewer'
    forms=[json.loads(line) for line in (reviewer/'blank-review-forms.jsonl').read_text().splitlines()]
    (output/'human-review/blank-import-result.json').write_bytes(json_bytes(import_reviews(reviewer,forms)))
    result['ready_rate']={'numerator':sum(c['state']=='ready' for c in result['cases']),'denominator':len(rows)}
    result['invariants_pass']=len(result['cases'])==len(rows) and all(c['parent_unchanged'] and c['original_source_scope_valid'] for c in result['cases'] if c['state']!='not_attempted') and result['workflow']['admitted']<=max_requests
    (output/'results.json').write_bytes(json_bytes(result))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--live-authorized',action='store_true',help='Explicit opt-in using previously authorised fictional data/provider scope')
    parser.add_argument('--corpus',type=Path,default=CORPUS,help='Separate frozen corpus; original v2 inputs remain unchanged')
    parser.add_argument('--max-requests',type=int,default=12,help='Explicit aggregate request cap, including syntax correction')
    args=parser.parse_args()
    if not 1 <= args.max_requests <= 120:parser.error('max-requests must be between 1 and 120')
    if not args.live_authorized:parser.error('Live collection requires explicit opt-in; no provider call made')
    result=collect(args.output,args.corpus,args.max_requests)
    if not result['invariants_pass']:raise SystemExit(1)


if __name__=='__main__':main()
