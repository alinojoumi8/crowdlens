# Evidence-quality evaluations

The local evaluator exercises real source admission, schemas, proposal persistence,
immutable revisions, retry and H1 recovery with synthetic inputs and scripted model
responses. It does not measure real model-output quality. Read the
[frozen definition](evidence-quality-definition-v1.md) and
[human review procedure](evidence-quality-human-review.md).

Corpus/assertion freeze: `d815c6d4370f26d04b3bfd88c08bcf1f93cf1ff0`.
Application baseline: `fbedf59752fbc3387e4aa164c2f6f5869d4744de`.
The [v1 manifest](../../backend/tests/fixtures/evidence_quality/v1/manifest.json)
hashes one development case and fourteen holdout cases. They contain fictional
parcel records, provenance, original source IDs, and expected structural behavior.
No private documents or reserved historical evaluation packets are included.

## Reproduce

Use the repository's frozen Python 3.11 environment; do not borrow another
worktree's mutable virtual environment. From the repository root:

```bash
UV_PYTHON=3.11 uv sync --frozen --dev --project backend
backend/.venv/bin/python backend/scripts/evaluate_evidence_quality.py \
  --output-dir /tmp/crowdlens-ecc-eval-RUN --repeats 3
```

Choose a new output directory each time. Exit 1 means a structural failure or an
unstable input identity; all run logs/results remain available. The script runs
the existing pytest runner with a socket connection guard, a synthetic provider
configuration and disposable databases/artifacts. H1 tests use local subprocesses.
No ECC candidate gate or alternative execution backend is invoked.

`results.json` records exact commit, dirty paths, allowlisted source/test hashes,
fixture freeze/hash, prompt hashes/configuration, grader/Python/platform, raw case
outcomes, test counts, timings and three repeat results. `run-N.xml` and `run-N.txt`
retain JUnit evidence and failure text. `human-review/reviewer` contains blinded
packets and blank forms; `administrator` contains the identity mapping.

The suite includes existing proposal, citation, retrieval, transport, revision,
API, scope-boundary and owned-task regressions. Those tests remain authoritative;
this runner does not duplicate their implementation. New corpus tests verify
expected admission and blocked states, schema fields, source hashes, immutable
child lineage, parent artifact hashes, retry identity and retained `needs_review`.

## Measurement boundaries

All test counts include failures/errors/skips. First-attempt success and all-repeat
stability report numerators/denominators. Blocked invalid proposals are counted as
blocked workflows even when the corresponding safety assertion passes. Corpus
substitute calls are measured separately; uninstrumented other test fakes have
unknown call counts. No provider-output accuracy, attribution accuracy, unsupported
claim rate, omission score, real model latency, cost or human effort is fabricated.

Source ID validity and literal/hash integrity are deterministic structural checks.
A valid citation to an irrelevant assertion can still pass with a permissive
scripted audit; the `semantic_gap` fixture makes that limitation visible. Conflict
and attribution packets need human assessment. All four accepted synthetic
holdout revisions remain Needs review; readiness does not certify factual support.

The root response-loss and concurrent-admission probes are fail-first regressions.
They capture dispatch and use real SQLite; they do not generate completed reports.
The default Anthropic retry probe replaces transport and sleep, recording five
300-second attempt limits and 30 seconds of backoff (1530 simulated seconds).
That is an aggregate retry characterization, not a passed report-budget acceptance
test or actual latency. A root-wide call/cost/deadline policy remains unresolved.

## Evidence status

The [preserved before baseline](2026-10-02-evidence-quality-baseline.md) tested clean
commit `86f5882c2ae369a0828113abbf640b814bb0574a`: all three runs collected 164 tests,
with 162 passing and the same two root-admission failures each time. The workflow
corpus had five ready proposals (one development) and ten blocked proposals per
run, all matching the frozen structural contracts. No application behavior was
changed by this evaluation work. The coordinator owns the duplicate-admission fix
and combined-candidate verification; the before evidence remains unchanged.

Model quality is **BLOCKED** by absent generation-model execution. Human labels
and measured effort are **PENDING**; four blinded packets and their blank forms
are [preserved here](results/2026-10-02-before/human-review/reviewer/blank-review-forms.jsonl).
Exact-candidate CI, real-service workflow and existing deployment verification
belong to separate workstreams. The importer subsequently received three schema/
partial-review regression tests; these additions do not alter the original
164-test receipt or its frozen corpus.
