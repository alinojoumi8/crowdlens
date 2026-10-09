"""Metered fictional source-draft verification; AI observations are not human labels."""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--suite', choices=['standard', 'continued-pages'], default='standard')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.parent != Path('/tmp') or not output.name.startswith('crowdlens-multidoc-') or output.exists():
        parser.error('Use a new /tmp/crowdlens-multidoc-* directory')
    from app.config import Config
    from app.services.evidence_drafting import EvidenceDraftingService
    from app.services.proposal_store import ProposalStore
    from app.services.report_agent import Report, ReportManager, ReportOutline, ReportSection, ReportStatus
    from app.services.report_revisions import ReportRevisionService
    from app.services.workflow_execution import WorkflowLedger, execution_scope
    from app.utils.draft_budget import DraftBudget
    from app.utils.llm_client import LLMClient
    from scripts.evidence_quality_support import FixtureStorage, artifact_hashes
    if Config.LLM_MODEL_NAME != args.model or Config.JEV_EVIDENCE_MODE != 'off':
        parser.error('Configured model must match explicit model; Jev evidence mode must be off')
    fixture_path = Path(__file__).resolve().parents[1] / 'tests/fixtures/multidocument_verification' / ('cases.json' if args.suite == 'standard' else 'continued-pages.json')
    raw = fixture_path.read_bytes()
    cases = json.loads(raw)
    output.mkdir()
    ReportManager.REPORTS_DIR = ReportManager.FALLBACK_REPORTS_DIR = str(output/'reports')
    ledger = WorkflowLedger(output/'control.sqlite')
    allowance = ledger.authorize(request_key=str(uuid.uuid4()), provider=Config.LLM_DEFAULT_PROVIDER,
        model=Config.LLM_MODEL_NAME, base_url=Config.LLM_BASE_URL,
        input_description='Three fictional multi-document source draft tests only',
        input_fingerprint=hashlib.sha256(raw).hexdigest(), max_requests=30, max_seconds=900, confirmed=True)
    observations = []
    for case in cases:
        scope = {k:'qa_'+case['id'] for k in ('graph_id','case_id','case_version_id')}
        sources = [{**scope,'uuid':case['id']+'_'+identifier,'document_id':identifier,
                    'filename':identifier+'.txt','data':text,'origin':'source_document','chunk_index':0}
                   for identifier,text in case['sources']]
        storage = FixtureStorage(sources)
        parent = Report('report_qa_'+case['id'], 'sim_qa_'+case['id'], scope['graph_id'], case['task'],
            ReportStatus.NEEDS_REVIEW, report_mode='legal_case', source_grounding=scope,
            outline=ReportOutline('Fictional QA: '+case['id'],case['summary'],
                [ReportSection(case['task'],content=case['summary']), ReportSection('Unselected',content='Unselected fictional text.')]))
        parent.markdown_content = parent.outline.to_markdown()
        ReportManager.save_report(parent)
        before = artifact_hashes(output/'reports'/parent.report_id)
        store = ProposalStore(ReportManager.REPORTS_DIR)
        record, lease = store.admit(parent.report_id, 'qa_'+case['id'], 'body_v1')
        store.update(record['proposal_id'], {'queued'}, {'state':'running','scope':scope,'section_index':1})
        try:
            with execution_scope(ledger, allowance['workflow_id'], 'proposal'):
                result = EvidenceDraftingService(storage, LLMClient(), store).generate(record['proposal_id'], parent.to_dict(), budget=DraftBudget())
        finally:
            lease.close()
        observation = {'case_id':case['id'],'task':case['task'],'sources':sources,'result':result,
                       'human_quality_labels':None,'human_review_seconds':None}
        if result['state'] == 'ready':
            service = ReportRevisionService(store, storage=storage)
            child = service.accept(parent.report_id,result['proposal_id'],result['proposal_digest'])
            assert child.status == ReportStatus.NEEDS_REVIEW and child.revision['immutable']
            assert child.outline.sections[1] == parent.outline.sections[1]
            assert service.accept(parent.report_id,result['proposal_id'],result['proposal_digest']).report_id == child.report_id
            observation['accepted_report_id'] = child.report_id
        assert artifact_hashes(output/'reports'/parent.report_id) == before
        observation['parent_unchanged'] = True
        observations.append(observation)
        (output/'observations.json').write_text(json.dumps(observations,indent=2))
        print(case['id'], result['state'], [f['code'] for f in result['findings']], flush=True)
    result = {'model':Config.LLM_MODEL_NAME,'fixture_sha256':hashlib.sha256(raw).hexdigest(),
              'workflow':ledger.status(allowance['workflow_id']), 'cases':observations}
    (output/'result.json').write_text(json.dumps(result,indent=2))
    def escaped(value): return html.escape(str(value))
    sections = []
    for row in observations:
        draft = row['result'].get('after') or {}
        sources_html = ''.join('<h3>'+escaped(s['filename'])+'</h3><p>'+escaped(s['data'])+'</p>' for s in row['sources'])
        sections.append('<section><h2>'+escaped(row['case_id'])+' · '+escaped(row['result']['state'])+'</h2><p>'+escaped(row['task'])+'</p><div class="columns"><article><h3>Original fictional sources</h3>'+sources_html+'</article><article><h3>Proposed section</h3><pre>'+escaped(draft.get('section','No completed draft'))+'</pre><h3>Proposed summary</h3><pre>'+escaped(draft.get('summary',''))+'</pre><h3>Review findings</h3><pre>'+escaped(json.dumps(row['result']['findings'],indent=2))+'</pre></article></div></section>')
    (output/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>CrowdLens fictional source verification</title><style>body{font:16px system-ui;margin:24px;color:#18202d}section{border-top:1px solid #bbb;padding:20px 0}.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}article{min-width:0}@media(max-width:700px){.columns{grid-template-columns:1fr}}</style><h1>CrowdLens fictional source verification</h1><p>Live model outputs compared with fictional sources. AI review, not factual certification or human quality labels. Parent reports preserved.</p>'+''.join(sections)+'</html>')


if __name__ == '__main__':
    main()
