"""Serve a disposable synthetic report using the real built frontend and report APIs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', action='store_true', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    from app.config import Config
    from app.services.report_agent import Report, ReportOutline, ReportSection, ReportStatus, ReportManager
    output = args.output_dir.resolve()
    forbidden = [Path(Config.UPLOAD_FOLDER).resolve(), Path(ReportManager.REPORTS_DIR).resolve(), Path(ReportManager.FALLBACK_REPORTS_DIR).resolve()]
    if (not output.is_relative_to(Path(tempfile.gettempdir()).resolve())
            or any(output == path or output.is_relative_to(path) for path in forbidden)
            or (output.exists() and any(output.iterdir()))):
        parser.error('Use a new empty directory beneath the system temporary directory, outside uploads.')
    output.mkdir(parents=True, exist_ok=True)
    frontend = BACKEND.parent / 'frontend' / 'dist'
    if not (frontend/'index.html').is_file():
        parser.error('Build the real frontend first: npm --prefix frontend run build')
    # Fail closed if any future code accidentally reaches a real provider.
    import requests
    import httpx
    def disabled(*a, **kw): raise RuntimeError('Providers are disabled in the synthetic harness')
    requests.Session.request = disabled
    httpx.Client.send = disabled
    Config.JEV_EVIDENCE_MODE = 'off'
    ReportManager.REPORTS_DIR = ReportManager.FALLBACK_REPORTS_DIR = str(output/'reports')
    scope = {'graph_id':'synthetic_graph','case_id':'synthetic_case','case_version_id':'synthetic_v1'}
    text = 'Alex states that the hearing was postponed until Friday.'
    parent = Report('report_synthetic', 'sim_synthetic', scope['graph_id'], 'Review the synthetic hearing record.', ReportStatus.NEEDS_REVIEW,
        report_mode='legal_case', source_grounding=scope, created_at='2026-09-21T12:00:00',
        forecast={'status':'unavailable','limitations':'Synthetic source-only example; no simulation has run.'},
        outline=ReportOutline('Synthetic hearing report', 'The hearing is Thursday. Other issues remain open.',
            [ReportSection('Hearing', content='The hearing is Thursday.'), ReportSection('Unrelated contracts', content='Unrelated contracts remain unresolved.')]))
    parent.markdown_content = parent.outline.to_markdown()
    ReportManager.save_report(parent)
    for i, section in enumerate(parent.outline.sections,1): ReportManager.save_section(parent.report_id,i,section)
    from app.services.proposal_store import ProposalStore
    store = ProposalStore(ReportManager.REPORTS_DIR)
    changed = [False]
    from scripts.evidence_quality_support import FixtureInventory
    class Storage(FixtureInventory):
        def get_source_chunks(self, **kw):
            return [{**scope,'uuid':'one','document_id':'synthetic_doc','filename':'synthetic-record.txt',
                     'data': text + (' Updated source.' if changed[0] else ''),'page':1,'chunk_index':0}]
    class LLM:
        model = 'synthetic-no-provider'
        def chat_json(self, messages, **kw):
            phase = messages[0]['content'].splitlines()[0]
            kw['usage_callback']('synthetic', self.model, {'input_tokens':0,'output_tokens':0}, 0)
            if phase == 'EVIDENCE_LEDGER_V1':
                return {'claims':[{'claim_id':'claim_01','kind':'attributed_allegation','text':text,
                    'attribution':'Alex','citation_ids':['episode:one'],'premise_claim_ids':[],'quote':''}],'gaps':[]}
            if phase == 'EVIDENCE_DRAFT_V1':
                return {'paragraphs':[{'text':text,'kind':'attributed_allegation','claim_ids':['claim_01']}],
                    'section_summary_claim_ids':['claim_01']}
            return {'audit_protocol':'target_reviews_v1','summary_consistent':True,
                'claim_reviews':[{'claim_id':'claim_01','outcome':'supported','evidence_ids':['episode:one'],
                    'detail':'Synthetic structural demonstration only; no factual label.'}],
                'paragraph_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic matched paragraph.'}],
                'summary_reviews':[{'target_index':0,'outcome':'supported','detail':'Synthetic claim-based summary.'}],
                'document_reviews':[{'document_id':'synthetic_doc','outcome':'complete','detail':'Synthetic one-source coverage.'}]}
    from flask import Flask, jsonify, send_from_directory
    from werkzeug.serving import make_server
    from app.api import report_bp
    from app.models.task import TaskManager
    TaskManager.configure_repository(None)
    app = Flask(__name__, static_folder=None)
    app.register_blueprint(report_bp,url_prefix='/api/report')
    app.extensions.update(neo4j_storage=Storage(), evidence_proposal_store=store,
                          evidence_llm_factory=lambda identifier: LLM(), evidence_embedder_factory=lambda: None)
    @app.get('/api/simulation/sim_synthetic')
    def simulation(): return jsonify(success=True,data={'simulation_id':'sim_synthetic','project_id':None})
    @app.get('/api/graph/<path:rest>')
    def graph(rest): return jsonify(success=True,data={'graph_id':scope['graph_id'],'status':'pass','nodes':[],'edges':[]})
    @app.post('/__synthetic/change-source')
    def change_source():
        changed[0] = True
        return jsonify(success=True)
    def digests():
        return {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (output/'reports'/'report_synthetic').iterdir() if path.is_file()}
    original = digests()
    (output/'parent-before.json').write_text(json.dumps(original,indent=2))
    @app.get('/__synthetic/evidence')
    def evidence():
        result = {'parent_unchanged':original == digests(), 'parent_digests':digests(),
                  'reports':[r.to_dict() for r in ReportManager.list_reports()], 'proposals':list(store.records())}
        (output/'browser-evidence.json').write_text(json.dumps(result,indent=2))
        return jsonify(result)
    @app.get('/')
    @app.get('/<path:path>')
    def frontend_file(path='index.html'):
        if path.startswith('api/'): return jsonify(success=False,error='synthetic_route_unavailable'),404
        return send_from_directory(frontend, path if (frontend/path).is_file() else 'index.html')
    server = make_server('127.0.0.1', args.port, app, threaded=True)
    print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}/report/report_synthetic',
                      'output_dir':str(output),'stop':'Ctrl-C in this process'}),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__': main()
