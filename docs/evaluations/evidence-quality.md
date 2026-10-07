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
changed by this evaluation work. The coordinator repaired duplicate admission and
ran a [comparable after baseline](2026-10-02-evidence-quality-after-root.md) on clean
`e5108ca62c63e91980183d658fd706fb48f1f21d`: all 164 tests passed in each of three
runs. Fixture and prompt hashes match; the before evidence remains unchanged.
The final combined candidate still requires the release owner's fresh verification.

For the original v1 corpus, model quality was **BLOCKED** by absent generation-model execution. Human labels
and measured effort are **PENDING**; four blinded packets and their blank forms
are [preserved here](results/2026-10-02-before/human-review/reviewer/blank-review-forms.jsonl).
Exact-candidate CI, real-service workflow and existing deployment verification
belong to separate workstreams. The importer subsequently received three schema/
partial-review regression tests; these additions do not alter the original
164-test receipt or its frozen corpus.

## Actual held-out collection follow-up

The [v2 source-review milestone](2026-10-03-source-review-v2.md) freezes separate inputs and preserves actual MiniMax-M3 proposal drafts: four attempted, four blocked, nine requests. The standalone browser review includes all current original documents, blank judgments, manual timing and partial JSONL export. Independent ratings and measured effort remain PENDING; this does not retroactively convert v1 scripted outputs into model-quality evidence. Application behavior is unchanged.

## Source coverage repair follow-up

[Source coverage and summary repair](../audits/2026-10-03-source-coverage-repair.md) implements bounded companion-document retrieval, source metadata preservation, planned-claim coverage and server-resolved exact summary spans. Final check passes 673 tests and build. Fresh v3 actual MiniMax verification retrieved all eight current originals, with one ready and three blocked proposals after 11 requests; strict guards and original reports are preserved. Independent Astra max review finds all 28 material section facts covered; 31 of 33 claim judgments are supported, one unsupported and one ambiguous. These AI opinions stay separate from still-unmeasured human labels/time. This does not establish broad factual quality or release readiness.

## 2026-10-04 contract verification

[Claim grounding and summary completion](../audits/2026-10-04-draft-contract-completion.md) passes 694 structural tests/build with independent code review. Fresh actual MiniMax v4/v5 both retain 0/4 ready outcomes, with 8/10 requests. Source-first Astra opinions remain AI; human truth labels and timing remain unmeasured. Full ledger review and server-owned summary scope improve contracts but do not establish semantic accuracy or factual certification. Preserve both frozen runs and use new verification inputs after separate development work.

## Output reliability follow-up — 2026-10-05

[JSON, summary and explicit audit contracts](../audits/2026-10-05-output-reliability.md) now build default summary wording from selected ledger claims, retain one counted syntax correction per phase, and require complete claim/paragraph/edit/document judgments for fresh proposals. Mixed or missing protocols and negative judgments block. Final check: 713 tests/build and independent code review pass. Fresh v6 MiniMax verification retains 4/4 ready proposals, 12 requests, all eight originals and unchanged parents; the final stricter gate revalidates those retained audits without rerunning v6. Astra max covers all 22 material facts and rates 24 of 25 claims supported, but flags one conditional-to-universal inference also repeated in its summary. Ready remains reviewable, not factual approval. Human ratings/time remain unmeasured; no actual proposal was accepted or published. Next: conditional implication and correction verification before release integration.
