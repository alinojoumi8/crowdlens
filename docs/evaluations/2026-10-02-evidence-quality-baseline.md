# Evidence-quality v1: before baseline

Date: 2026-10-02. Milestone 3 evaluation specialist. Skills: installed ECC 2.2.3
`eval-harness` and `ai-regression-testing`, applied to repository-native pytest.

**Harness and deterministic before baseline: COMPLETE. Baseline hard-invariant
verdict: PARTIAL**, because two root-admission safety assertions fail. **Real
model-output quality: BLOCKED. Human quality review: PENDING.** The failure
receipts are preserved; their assertions were not weakened. This report is not a
release, deployment or factual-quality verdict.

## Identity and reproduction

| Input | Exact identity |
| --- | --- |
| Assigned starting commit | `fbedf59752fbc3387e4aa164c2f6f5869d4744de` (H1 code `33d87c82c5f3ecb3435ba86a5160a44f79635443` plus M1 docs) |
| Corpus/assertion freeze, before any run | `d815c6d4370f26d04b3bfd88c08bcf1f93cf1ff0` |
| Tested harness/source commit | `86f5882c2ae369a0828113abbf640b814bb0574a` |
| Dirty/untracked inputs during baseline | Empty git status; identity before/after equal |
| Full allowlisted input manifest SHA-256 | `8caf50c694fa00290bac303d8bbdca80a2000d33cd5291ce0e39a5b8f1095e2e` |
| Runtime-source-v1 SHA-256 | `c39d53344feb312ac7fe3c87d3da99367bda2f7f0e0c7913c5d4b649173ccb15` |
| Fixture manifest SHA-256 | `78dc98ecd30ac22f14aa40c4ae8635145b43801f257af623f7d00abe89a5b12f` |
| Environment | Independent `.venv`, Python 3.11.15; frozen `uv sync --offline --dev`, 146 packages |

Exact baseline command (repository root), **exit 1**:

```bash
backend/.venv/bin/python backend/scripts/evaluate_evidence_quality.py \
  --output-dir /tmp/crowdlens-ecc-eval-before-20261002 --repeats 3
```

The runner refuses reuse of an output directory. Choose another name for replay.
The frozen-commit version collects 164 tests; later importer regression additions
make the current suite larger. Do not relabel a current run as this historical
baseline. All application files in the baseline match the assigned starting
application source. Evaluation files and documentation are the only edits.

The durable [results JSON](results/2026-10-02-before/results.json) contains every
test outcome, fault observation, corpus proposal/claim/source observation, exact
prompt hashes, provider/model substitution, command/exit code and file digest.
[Run 1](results/2026-10-02-before/run-1.xml),
[run 2](results/2026-10-02-before/run-2.xml), and
[run 3](results/2026-10-02-before/run-3.xml) preserve JUnit data; companion `.txt`
files preserve failure output. [Receipt hashes](results/2026-10-02-before/receipt-sha256.json)
allow byte-for-byte verification of the copied results. These are local integrity
records, not signed attestations or ECC containment receipts.

## Measured results

| Measure | Observed result / denominator |
| --- | --- |
| Run 1 | 162 passed, 2 failed, 164 collected; 6.086 seconds harness wall time |
| Run 2 | 162 passed, 2 failed, 164 collected; 5.543 seconds |
| Run 3 | 162 passed, 2 failed, 164 collected; 6.029 seconds |
| First attempt | 162 / 164 = 98.78% |
| Passed at least once in three | 162 / 164 = 98.78% |
| Passed all three | 162 / 164 = 98.78% |
| Repeated observations | 486 passed, 6 failed; zero skips, errors or missing repeats |
| Corpus workflow outputs | Per run: 5 ready, 10 blocked / 15 cases (14 holdout + 1 development) |
| Holdout workflow outputs | Per run: 4 ready, 10 blocked / 14 cases |
| Corpus substitute invocations | 18 / run, 54 over all repeats; zero real model calls |
| Synthetic proposal service time | 45 observations, median 0.00249 seconds, range 0.00184–0.05033 seconds |
| Human reviews | 0 complete / 4 blinded packets; blank import status PENDING |
| Real provider quality/attribution/unsupported rate/omissions/latency/cost | null — no real model output or independent reference labels |

The first-attempt/stability denominator includes the failing root regressions.
Correct refusal of invalid evidence passes the safety assertion but remains a
blocked workflow. Ready outputs include a deliberately unsupported semantic
claim linked to a valid source and accepted by the scripted audit. Thus neither
ready count nor citation linkage is a factual accuracy score. The corpus has no
independent human truth/omission labels, and its authored expectations only define
structural behavior. Existing tests outside the corpus have uninstrumented fake
call counts; those counts remain null instead of being folded into 54.

## Confirmed fault and bounded interpretation

`test_lost_root_response_retry_does_not_dispatch_twice` loses the first HTTP
response to the caller and repeats the same synthetic request key. Each attempt
returns 200 and persists a different task/report ID; two dispatches are captured.
`test_concurrent_root_requests_admit_one_attempt` launches two Flask clients
together and observes the same duplicate admission. Both fail on all three runs.
SQLite, task ownership and Flask routing are real; actual generation is captured.
This establishes duplicate expensive-work admission, not completed duplicate
artifacts or measured provider cost. The coordinator received the frozen failing
test commit before implementing the application fix.

`test_anthropic_retry_budget_observation_is_per_attempt` injects a full timeout
at every transport attempt with default retry values. It records five attempts
of 300 seconds and backoffs of 2, 4, 8 and 16 seconds: **1530 simulated seconds**.
No provider call or real sleep occurs. It characterizes per-attempt amplification;
it does not prove a violation of a specified aggregate deadline, which does not
exist for the root workflow. Root-wide call/cost/deadline policy remains an
operational backlog item. Proposal DraftBudget and zero-retry boundaries are
separate contracts, verified by the existing proposal/transport tests.

## Human review and subsequent harness review

Four packets cover direct support/omissions, conflicting source accounts,
unsupported semantic content with valid citation identity, and attributed claims.
The [rubric and import procedure](evidence-quality-human-review.md) require actual
reviewer provenance and preserve disagreements. Original fixture/provider/category
and expected fields are withheld; source/document/case identifiers are remapped.
The [administrative mapping](results/2026-10-02-before/human-review/administrator/mapping.json)
is separate and must not be given to a blinded reviewer.

The baseline's untouched blank forms import to four pending forms and null quality
and time. Subsequent coordinator and specialist review identified that metadata-
only filled forms could be overcounted. Follow-up fail-first importer tests observed
two failures (metadata-only and partial ratings) before tightening classification.
The final importer keeps metadata-only forms pending, partial labels partial, and
requires all claim dimensions before counting a packet reviewed. Explicit schema
validation prevents missing-field KeyErrors. Eleven importer/metric tests pass;
the original baseline receipts remain unchanged. `LABELS_IMPORTED` still means
neither adjudication nor sign-off.

## Remaining evidence and ownership

1. Coordinator: integrate the concrete root-admission repair, run these frozen
   assertions on the combined candidate and preserve new after results with that
   exact commit. This historical baseline must remain red.
2. Operator/model owner: provide an authorized, suitable already-installed local
   generation model in isolated bounded configuration (or separately authorize its
   setup). Record model pin, actual outputs/calls and timings before scoring model
   quality. No generation model was downloaded or hosted inference called here.
3. Human-review owner: assign actual reviewers, collect completed forms and
   measured effort, preserve disagreements, then separately adjudicate. Omissions
   require a source-backed reference assessment. Four blank forms are ready.
4. Coordinator/product owner: define a root-wide aggregate call/cost/deadline
   policy before implementing and testing it. Do not mistake per-transport bounds
   or proposal deadlines for a complete report budget.
5. Release owner: separately verify real Neo4j/OASIS/model workflow, existing
   deployment and exact-candidate remote CI when their authorizations/prerequisites
   exist. This offline harness does not substitute for those checks.
