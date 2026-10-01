"""Run a public-opinion, real-model evidence draft in disposable local storage.

The baseline and proposal use the same configured LLM. Only the four-page
majority opinion is sent to it; the source PDF and report files stay local.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

SOURCE_URL = 'https://www.supremecourt.gov/opinions/23pdf/22-429_h315.pdf'
SOURCE_SHA256 = '7dba0b08254d8d0eccd91ccfe915ecccd33ac1daaada7daabcae3f5bc743a952'
PRICE_URL = 'https://platform.minimax.io/subscribe/token-plan?tab=api-enterprise'
SCOPE = {'graph_id': 'public_acheson_graph', 'case_id': 'public_acheson_case',
         'case_version_id': 'public_acheson_opinion_2023_12_05'}
REPORT_ID = 'report_public_acheson_baseline'
SIMULATION_ID = 'sim_public_acheson'


def page_text(pdf, pdf_page):
    result = subprocess.run(['pdftotext', '-f', str(pdf_page), '-l', str(pdf_page),
                             '-layout', str(pdf), '-'], capture_output=True, text=True,
                            check=True)
    # Preserve wording while joining PDF line wraps. The original PDF remains
    # the review authority, and every normalized source chunk is hashed.
    text = re.sub(r'(?<=\w)-\s*\n\s*(?=\w)', '', result.stdout)
    return re.sub(r'\s+', ' ', text).strip()


def estimated_cost(usage, model):
    if model != 'MiniMax-M3' or not usage or not usage.get('calls'):
        return None
    total = 0.0
    for call in usage['calls']:
        if type(call.get('input_tokens')) is not int or type(call.get('output_tokens')) is not int:
            return None
        total += (call['input_tokens'] * .3 + call['output_tokens'] * 1.2) / 1_000_000
    return round(total, 6)


def comparison(output, baseline, proposal, source_chunks, model, pdf_digest, attempts):
    proposed = proposal.get('after') or {}
    usage = proposal.get('usage') or {}
    by_id = {'episode:' + item['uuid']: item for item in source_chunks}
    source_claims = [item for item in proposal.get('ledger', []) if item.get('kind') != 'analysis']
    citations = sum(len(item.get('citation_ids') or []) for item in source_claims)
    exact_quotes = [item for item in source_claims if item.get('quote')]
    quote_matches = sum(any(item['quote'] in by_id[identifier]['data']
                            for identifier in item.get('citation_ids', []) if identifier in by_id)
                        for item in exact_quotes)
    report = {
        'source': {'url': SOURCE_URL, 'sha256': pdf_digest, 'pdf_pages_used': [2, 3, 4, 5],
                   'opinion_pages_used': [1, 2, 3, 4], 'chunk_count': len(source_chunks),
                   'scope': SCOPE},
        'model': model,
        'baseline': {'section': baseline['section'], 'summary': baseline['summary'],
                     'usage': baseline['usage'], 'elapsed_seconds': baseline['elapsed_seconds'],
                     'estimated_usd': estimated_cost(baseline['usage'], model)},
        'proposed': {'proposal_id': proposal.get('proposal_id'), 'state': proposal.get('state'),
                     'section': proposed.get('section'), 'summary': proposed.get('summary'),
                     'usage': usage, 'timing': proposal.get('timing'),
                     'elapsed_seconds': round(usage.get('elapsed_ms', 0) / 1000, 2) if usage else None,
                     'estimated_usd': estimated_cost(usage, model),
                     'source_claim_count': len(source_claims), 'citation_count': citations,
                     'exact_quote_count': len(exact_quotes), 'exact_quotes_found': quote_matches,
                     'retrieved_source_count': len(proposal.get('sources') or []),
                     'findings': proposal.get('findings'), 'limitations': proposal.get('limitations')},
        'review_status': 'pending_human_review',
        'factual_accuracy': None,
        'attribution_accuracy': None,
        'citation_validity_reviewed': None,
        'human_review_seconds': None,
        'pricing': {'url': PRICE_URL, 'input_usd_per_million': .3,
                    'output_usd_per_million': 1.2, 'basis': 'published MiniMax-M3 standard priority, context <=512K; estimate only'},
        'trial_attempts': [
            {'proposal_id': item.get('proposal_id'), 'state': item.get('state'),
             'findings': item.get('findings') or [], 'usage': item.get('usage') or {},
             'estimated_usd': estimated_cost(item.get('usage') or {}, model)}
            for item in sorted(attempts, key=lambda row: row['created_at'])
        ],
    }
    (output / 'measurements.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    after_section = proposed.get('section') or '[No draft section available; inspect proposal findings.]'
    after_summary = proposed.get('summary') or '[No draft summary available.]'
    lines = [
        '# Public opinion evidence-draft review', '',
        f'Official PDF: {SOURCE_URL}',
        f'PDF SHA-256: `{pdf_digest}`',
        'Source subset: the four majority-opinion pages (PDF pages 2–5). The syllabus and concurrences are excluded.',
        'The extracted text joins PDF line breaks. Check wording and context against the linked PDF.', '',
        f'Model for both paths: **{model}**. The baseline uses one direct call; the evidence-first path plans a ledger, drafts, and audits.',
        f'Proposal state: **{proposal.get("state", "not_started")}**. Human factual review is pending.', '',
        '## Baseline section', '', baseline['section'], '',
        '## Evidence-first section', '', after_section, '',
        '## Baseline summary', '', baseline['summary'], '',
        '## Evidence-first summary', '', after_summary, '',
        '## Measurements', '',
        f'- Baseline: {baseline["elapsed_seconds"]:.2f} s, '
        f'{len(baseline["usage"]["calls"])} model call; estimated cost {report["baseline"]["estimated_usd"]} USD.',
        f'- Evidence-first: {report["proposed"]["elapsed_seconds"]} s, '
        f'{len(usage.get("calls", []))} model calls; estimated cost {report["proposed"]["estimated_usd"]} USD.',
        f'- Structured source claims: {len(source_claims)}; citation links: {citations}; '
        f'optional verbatim quote fields: {len(exact_quotes)} '
        f'({quote_matches} matched cited source chunks).',
        '- Factual correctness, attribution correctness, omissions, and human review time await your review.',
        f'- The price estimate uses [published MiniMax-M3 standard-priority rates]({PRICE_URL}). Actual billing may differ by plan and caching.', '',
        '## Trial history', '',
    ]
    for attempt in report['trial_attempts']:
        codes = ', '.join(sorted({row['code'] for row in attempt['findings']})) or 'none'
        calls = len(attempt['usage'].get('calls', []))
        lines.append(f'- `{attempt["proposal_id"]}`: {attempt["state"]}; findings: {codes}; '
                     f'{calls} model call{"s" if calls != 1 else ""}; '
                     f'estimated cost {attempt["estimated_usd"]} USD.')
    lines.extend(['',
        '## Your review', '',
        'The majority opinion says Laufer did not argue that the Court **must** dismiss for mootness. Check whether both drafts overstate her position by saying she urged dismissal.',
        '',
        '| Measure | Baseline | Evidence-first |',
        '| --- | --- | --- |',
        '| Factual errors | pending | pending |',
        '| Attribution errors | pending | pending |',
        '| Citation meaning and page match | n/a | pending |',
        '| Material omissions | pending | pending |',
        '| Human review time | pending | pending |', '',
        '- [ ] Check each factual statement in both sections against the PDF.',
        '- [ ] Check whose position each statement represents: the Court, Laufer, or Acheson.',
        '- [ ] Check source page links and whether cited excerpts support the full meaning of each claim.',
        '- [ ] Note important omissions and whether the revised summary reflects the Court’s actual disposition.',
        '- [ ] Record your review time and any errors before deciding whether to save the revision.', '',
        '## Reproduce', '',
        'Build the frontend, provide an existing local `.env` with MiniMax credentials, and use a new empty directory under `/tmp`:', '',
        '```bash',
        'UV_PYTHON=3.11 uv run --frozen --directory backend python scripts/public_evidence_demo.py \\',
        '  --pdf /path/to/22-429_h315.pdf --model-env /path/to/.env \\',
        '  --output-dir /tmp/mirofish-public-evidence-replay',
        '```', '',
        'The script refuses a PDF with a different SHA-256 and leaves any accepted revision to the reviewer.', '',
    ])
    (output / 'review.md').write_text('\n'.join(lines), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--model-env', type=Path, default=BACKEND.parent / '.env',
                        help='Path to an existing .env containing the configured LLM credentials.')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--resume-output', action='store_true',
                        help='Reuse the pinned public source and baseline after a stopped demo server.')
    args = parser.parse_args()
    output, pdf = args.output_dir.resolve(), args.pdf.resolve()
    from dotenv import dotenv_values
    settings = dotenv_values(args.model_env)
    for key in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL_NAME'):
        if settings.get(key):
            os.environ[key] = settings[key]
    os.environ['JEV_EVIDENCE_MODE'] = 'off'
    if not settings.get('LLM_API_KEY'):
        parser.error('The configured drafting model is unavailable.')
    from app.config import Config
    from app.services.report_agent import Report, ReportOutline, ReportSection, ReportStatus, ReportManager
    from app.services.proposal_store import ProposalStore
    from app.utils.draft_budget import DraftBudget
    from app.utils.llm_client import LLMClient
    forbidden = [Path(Config.UPLOAD_FOLDER).resolve(), Path(ReportManager.REPORTS_DIR).resolve(),
                 Path(ReportManager.FALLBACK_REPORTS_DIR).resolve()]
    if (not output.is_relative_to(Path(tempfile.gettempdir()).resolve())
            or any(output == path or output.is_relative_to(path) for path in forbidden)
            or (not args.resume_output and output.exists() and any(output.iterdir()))):
        parser.error('Use a new empty temporary output directory outside normal uploads.')
    data = pdf.read_bytes()
    pdf_digest = hashlib.sha256(data).hexdigest()
    if pdf_digest != SOURCE_SHA256:
        parser.error('The public PDF differs from the verified source version.')
    chunks = []
    for pdf_page in range(2, 6):
        excerpt = page_text(pdf, pdf_page)
        if not excerpt or len(excerpt) > 5000:
            parser.error(f'Cannot safely extract PDF page {pdf_page}.')
        chunks.append({**SCOPE, 'uuid': f'opinion_page_{pdf_page}', 'document_id': 'supreme_court_22_429',
                       'filename': 'Acheson Hotels v. Laufer, majority opinion', 'data': excerpt,
                       'page': pdf_page, 'chunk_index': pdf_page - 2, 'origin': 'source_document'})
    if args.resume_output:
        try:
            previous_chunks = json.loads((output / 'source-pages.json').read_text())
            baseline = json.loads((output / 'baseline.json').read_text())
        except (OSError, ValueError) as exc:
            parser.error(f'Cannot resume without the source pages and baseline: {exc}')
        if previous_chunks != chunks or not (output / 'reports' / REPORT_ID / 'meta.json').is_file():
            parser.error('The existing source pages or report do not match this pinned demo.')
    else:
        output.mkdir(parents=True)
        (output / 'source-pages.json').write_text(json.dumps(chunks, indent=2, ensure_ascii=False))
    frontend = BACKEND.parent / 'frontend' / 'dist'
    if not (frontend / 'index.html').is_file():
        parser.error('Build the frontend before starting the demo.')
    Config.JEV_EVIDENCE_MODE = 'off'
    ReportManager.REPORTS_DIR = ReportManager.FALLBACK_REPORTS_DIR = str(output / 'reports')
    llm = LLMClient()
    if not args.resume_output:
        budget = DraftBudget(seconds=90)
        material = '\n'.join(f'PDF page {row["page"]}: {row["data"]}' for row in chunks)
        baseline_prompt = (
            'Write a concise neutral report section about the mootness and disputed standing issue in '
            'Acheson Hotels, LLC v. Laufer. Use only the supplied opinion text. State the positions of '
            'Laufer and Acheson as positions, identify what the Court actually decided, and keep legal '
            'questions it did not decide separate. Return JSON with exactly "section" and "summary" '
            'strings. The section should be 2–4 short sentences; the summary one sentence. '
            'No outside facts, legal advice, or invented quotations.'
        )
        started = time.monotonic()
        baseline_result = llm.chat_json([
            {'role': 'system', 'content': baseline_prompt},
            {'role': 'user', 'content': material},
        ], temperature=0, max_tokens=1800, request_timeout=90, request_max_retries=0,
            usage_callback=budget.record_usage)
        if (not isinstance(baseline_result, dict)
                or any(not isinstance(baseline_result.get(key), str) or not baseline_result[key].strip()
                       or len(baseline_result[key]) > 4000 for key in ('section', 'summary'))):
            raise ValueError('The model did not return a usable baseline report.')
        baseline = {'section': baseline_result['section'].strip(), 'summary': baseline_result['summary'].strip(),
                    'usage': budget.snapshot(), 'elapsed_seconds': round(time.monotonic() - started, 2)}
        (output / 'baseline.json').write_text(json.dumps(baseline, indent=2, ensure_ascii=False))
        report = Report(REPORT_ID, SIMULATION_ID, SCOPE['graph_id'],
            'Compare a baseline report and an evidence-first draft against the public Court opinion.',
            ReportStatus.NEEDS_REVIEW, report_mode='legal_case', source_grounding=SCOPE,
            created_at=datetime.now(timezone.utc).isoformat(),
            forecast={'status': 'unavailable', 'limitations': 'Public opinion only; no simulation was run.'},
            outline=ReportOutline('Acheson Hotels v. Laufer — public source review', baseline['summary'], [
                ReportSection('Mootness and disputed standing', content=baseline['section'],
                              description='Laufer and Acheson positions, the Supreme Court disposition, and the standing question left unresolved.'),
                ReportSection('Review scope', content='Only the four majority-opinion pages are included as source material. The syllabus and concurrences are excluded.')]))
        report.markdown_content = report.outline.to_markdown()
        ReportManager.save_report(report)
        for index, section in enumerate(report.outline.sections, 1):
            ReportManager.save_section(report.report_id, index, section)
    store = ProposalStore(ReportManager.REPORTS_DIR)
    class PublicStorage:
        def get_source_chunks(self, **scope):
            return [dict(row) for row in chunks if all(row.get(key) == value for key, value in scope.items())]
    from flask import Flask, jsonify, send_file, send_from_directory
    from werkzeug.serving import make_server
    from app.api import report_bp
    from app.models.task import TaskManager
    TaskManager.configure_repository(None)
    app = Flask(__name__, static_folder=None)
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.extensions.update(neo4j_storage=PublicStorage(), evidence_proposal_store=store,
                          evidence_llm_factory=lambda identifier: LLMClient(),
                          evidence_embedder_factory=lambda: None)
    @app.get('/api/simulation/<simulation_id>')
    def simulation(simulation_id):
        return jsonify(success=True, data={'simulation_id': simulation_id, 'project_id': None})
    @app.get('/api/graph/<path:rest>')
    def graph(rest):
        return jsonify(success=True, data={'graph_id': SCOPE['graph_id'], 'status': 'pass', 'nodes': [], 'edges': []})
    @app.get('/public-source.pdf')
    def source_pdf():
        return send_file(pdf, mimetype='application/pdf', as_attachment=False,
                         download_name='acheson-hotels-v-laufer.pdf')
    @app.get('/public-comparison')
    def public_comparison():
        records = list(store.records())
        if not records:
            return jsonify(success=False, error='proposal_not_started'), 404
        record = sorted(records, key=lambda item: item['created_at'])[-1]
        if record['state'] in {'queued', 'running'}:
            return jsonify(success=False, error='proposal_in_progress'), 202
        return jsonify(success=True, data=comparison(output, baseline, record, chunks, llm.model, pdf_digest, records))
    @app.get('/')
    @app.get('/<path:path>')
    def frontend_file(path='index.html'):
        if path.startswith('api/'):
            return jsonify(success=False, error='route_unavailable'), 404
        return send_from_directory(frontend, path if (frontend / path).is_file() else 'index.html')
    server = make_server('127.0.0.1', args.port, app, threaded=True)
    print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}/report/{REPORT_ID}',
                      'source_url': SOURCE_URL, 'model': llm.model, 'output_dir': str(output),
                      'stop': 'Stop this local process'}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
