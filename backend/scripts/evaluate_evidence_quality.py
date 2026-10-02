"""Run the local structural baseline with pytest; no inference or quality labels."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from scripts.evidence_quality_support import CORPUS_ROOT, load_corpus, sha256
from scripts.evidence_quality_reviews import export_packets, import_reviews, json_bytes, rate

SUITE = [
    'tests/test_evidence_quality_corpus.py', 'tests/test_evidence_quality_faults.py',
    'tests/test_evidence_quality_harness.py', 'tests/test_claim_ledger.py',
    'tests/test_evidence_drafting.py', 'tests/test_evidence_proposals_api.py',
    'tests/test_report_revisions.py', 'tests/test_source_retrieval.py',
    'tests/test_draft_transports.py', 'tests/test_draft_budget.py',
    'tests/test_task_ownership.py', 'tests/test_milestone2_boundaries.py',
]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def input_identity():
    # Explicit source allowlist excludes uploads, local env/secrets and reserved evaluations.
    names = git('ls-files', '--', 'backend/app', 'backend/scripts', 'backend/tests',
                'backend/pyproject.toml', 'backend/uv.lock', 'frontend/src/api', 'package.json').splitlines()
    names += git('ls-files', '--others', '--exclude-standard', '--', 'backend/scripts',
                 'backend/tests/test_evidence_quality*', 'backend/tests/fixtures/evidence_quality').splitlines()
    digests = {name: sha256((ROOT / name).read_bytes()) for name in sorted(set(names)) if (ROOT / name).is_file()}
    return {'git_commit': git('rev-parse', 'HEAD'), 'git_branch': git('branch', '--show-current'),
            'dirty_status': git('status', '--porcelain=v1'), 'input_files_sha256': digests,
            'input_manifest_sha256': sha256(json_bytes(digests)),
            'fixture_freeze_commit': git('log', '-1', '--format=%H', '--', str(CORPUS_ROOT.relative_to(ROOT))),
            'fixture_manifest_sha256': sha256((CORPUS_ROOT / 'manifest.json').read_bytes())}


def parse_junit(path):
    cases = []
    for element in ET.parse(path).getroot().iter('testcase'):
        status = 'error' if element.find('error') is not None else 'failed' if element.find('failure') is not None else 'skipped' if element.find('skipped') is not None else 'passed'
        properties = {}
        for prop in element.findall('./properties/property'):
            value = prop.get('value')
            if prop.get('name') in {'corpus_observation', 'fault_observation', 'parent_artifact_hashes_after'}:
                value = json.loads(value)
            properties[prop.get('name')] = value
        cases.append({'id': element.get('classname', '') + '::' + element.get('name', ''),
                      'status': status, 'elapsed_seconds': float(element.get('time', 0)),
                      'properties': properties,
                      'failure': next((child.get('message') for child in element if child.tag in {'error', 'failure', 'skipped'}), None)})
    return cases


def summarize_runs(runs):
    identities = {case['id'] for run in runs for case in run['cases']}
    first = {case['id']: case['status'] for case in runs[0]['cases']} if runs else {}
    outcomes = [{case['id']: case['status'] for case in run['cases']} for run in runs]
    stable = [identifier for identifier in identities if all(run.get(identifier) == 'passed' for run in outcomes)]
    once = [identifier for identifier in identities if any(run.get(identifier) == 'passed' for run in outcomes)]
    success = bool(identities) and all(run['exit_code'] == 0 for run in runs) and len(stable) == len(identities)
    corpus = [case['properties']['corpus_observation'] for run in runs for case in run['cases']
              if 'corpus_observation' in case['properties']]
    return {'status': 'COMPLETE' if success else 'PARTIAL', 'runs': len(runs), 'unique_test_count': len(identities),
            'first_attempt_success': rate(sum(status == 'passed' for status in first.values()), len(identities)),
            'pass_at_k': rate(len(once), len(identities)), 'pass_power_k': rate(len(stable), len(identities)),
            'counts_across_runs': dict(Counter(case['status'] for run in runs for case in run['cases'])),
            'missing_test_observations': sum(identifier not in run for identifier in identities for run in outcomes),
            'corpus_workflow_outcomes': dict(Counter(row['state'] for row in corpus)),
            'corpus_substitute_calls': sum(row['substitute_calls'] for row in corpus),
            'corpus_real_model_calls': sum(row['real_model_calls'] for row in corpus),
            'all_suite_substitute_calls': None,
            'model_quality': {'status': 'BLOCKED', 'outputs': 0, 'source_attribution_accuracy': None,
                              'unsupported_claim_rate': None, 'omissions': None, 'human_review_seconds': None,
                              'provider_latency_seconds': None, 'cost': None},
            'denominator_policy': 'All collected unique test IDs, including failed/error/skipped and missing repeats. Correctly blocked workflow cases pass safety assertions but are not successful drafts.',
            'latency_scope': 'pytest wall time and synthetic proposal service time only; not model or production latency.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--repeats', type=int, choices=range(1, 4), default=3)
    args = parser.parse_args()
    output = args.output_dir.absolute()
    if output.parent.resolve() != Path(tempfile.gettempdir()).resolve() or not output.name.startswith('crowdlens-ecc-eval-'):
        parser.error('use a new direct /tmp/crowdlens-ecc-eval-* output directory')
    if output.exists():
        parser.error('output already exists; preserve earlier evidence and choose a new directory')
    fixtures = load_corpus('holdout')
    load_corpus('development')
    identity = input_identity()
    output.mkdir()
    (output / 'identity-before.json').write_bytes(json_bytes(identity))
    environment = dict(os.environ, PYTHONPATH=str(BACKEND), LLM_API_KEY='synthetic-offline-evaluation',
                       LLM_BASE_URL='http://127.0.0.1:1/v1', LLM_MODEL_NAME='synthetic-offline-evaluation',
                       JEV_INTERVIEW_MODE='off', JEV_RERANK_MODE='off', JEV_EVIDENCE_MODE='off')
    runs = []
    for number in range(1, args.repeats + 1):
        xml = output / f'run-{number}.xml'
        command = [sys.executable, '-m', 'pytest', '-p', 'scripts.evidence_quality_pytest', *SUITE,
                   '-q', '-o', 'junit_family=legacy', '--junitxml=' + str(xml),
                   '--basetemp=' + str(output / f'pytest-{number}')]
        started = time.monotonic()
        with (output / f'run-{number}.txt').open('w') as log:
            process = subprocess.run(command, cwd=BACKEND, env=environment, stdout=log, stderr=subprocess.STDOUT)
        cases = parse_junit(xml) if xml.exists() else []
        run = {'number': number, 'command': command, 'exit_code': process.returncode,
               'elapsed_seconds': time.monotonic() - started, 'cases': cases}
        runs.append(run)
        print(json.dumps({'run': number, 'exit_code': process.returncode, 'cases': len(cases),
                          'counts': dict(Counter(case['status'] for case in cases))}), flush=True)
    summary = summarize_runs(runs)
    observations = [case['properties']['corpus_observation'] for case in runs[0]['cases']
                    if 'corpus_observation' in case['properties']]
    review = export_packets(output / 'human-review', fixtures, observations)
    forms_path = output / 'human-review/reviewer/blank-review-forms.jsonl'
    forms = [json.loads(line) for line in forms_path.read_text().splitlines()]
    (output / 'human-review/blank-import-result.json').write_bytes(json_bytes(import_reviews(forms_path.parent, forms)))
    from app.services.evidence_drafting import LEDGER_PROMPT, DRAFT_PROMPT, AUDIT_PROMPT, POLICY
    from app.utils.build_identity import source_identity
    result = {'schema_version': 1, 'grader': 'pytest-structural-evidence-quality-v1',
              'created_at': datetime.now(timezone.utc).isoformat(), 'identity': identity,
              'identity_after': input_identity(), 'runtime_source_identity': source_identity(ROOT, identity['git_commit']),
              'python': platform.python_version(), 'platform': platform.platform(),
              'configuration': {'provider': 'deterministic_substitute', 'model': 'synthetic-scripted-draft-v1',
                                'policy': POLICY, 'JEV_EVIDENCE_MODE': 'off', 'semantic_embedder': None,
                                'temperature': 0, 'max_tokens': 6000, 'proposal_deadline_seconds': 180,
                                'request_max_retries': 0, 'network_guard': 'socket connect/connect_ex/create_connection refused in pytest process',
                                'prompt_sha256': {name: sha256(prompt.encode()) for name, prompt in
                                                   [('ledger', LEDGER_PROMPT), ('draft', DRAFT_PROMPT), ('audit', AUDIT_PROMPT)]}},
              'real_components': ['Flask test-client routes', 'SQLite task persistence', 'task runtime and H1 subprocesses',
                                  'source admission and lexical retrieval', 'schema and citation checks',
                                  'filesystem proposal snapshots and immutable revisions'],
              'substitutes': ['source storage rows from synthetic JSON; no Neo4j', 'scripted ledger/prose/audit; no generation model',
                             'root generation dispatch captured', 'provider timeout and sleep replaced for aggregate probe'],
              'summary': summary, 'human_review': review, 'runs': runs,
              'gaps': ['No real generation model or independently judged model outputs.',
                       'No human reviewer labels or measured review effort; blank forms remain pending.',
                       'Root aggregate call/cost/deadline policy remains undefined; per-attempt retry probe is characterization, not acceptance.',
                       'No end-to-end Neo4j/OASIS/model workflow, deployment check or exact-candidate remote CI in this harness.']}
    unchanged = result['identity_after'] == identity
    result['inputs_unchanged_during_run'] = unchanged
    if not unchanged:
        summary['status'] = 'PARTIAL'
        result['gaps'].append('Input identity changed during the run; candidate result is not stable.')
    (output / 'results.json').write_bytes(json_bytes(result))
    print(json.dumps({'summary': summary, 'human_review': review, 'output': str(output / 'results.json')}, indent=2))
    return 0 if summary['status'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
