# CrowdLens ECC execution handoff — 2026-10-02

Coordinator: primary implementation agent, with three isolated specialists and a
fresh independent AI reviewer in a freed slot. Local integration only. Scoped
implementation, authorized local verification and independent AI review are
complete. Model/human quality, full live workflow, remote CI and
existing deployment verification remain separate gaps below.

## Candidate and preserved work

- Branch: `codex/crowdlens-ecc-integration`.
- Frozen application/tests/dependencies/build commit:
  `242b8999044e33c8c3217df857c06401f3efbba3`.
- Frozen Git tree: `39753400064fe764b98152c2c0204005f874a9c1`.
- Runtime source fingerprint (`runtime-source-v1`):
  `a807c651b35560c12a91ec6f0b79b2d32df7bad60ebf3322d121c643d9e835fb`.
- Integration worktree: `/home/ali/.codex/worktrees/crowdlens-ecc-integration/mirofish-local`.
- Reporting-only documentation/evidence commits follow the tested candidate;
  they do not inherit an exact-head CI claim. The final chat identifies the
  resulting documentation HEAD separately.
- `main` remains `34275b75223dee82087ff6ac937c4fc6e4af9323`. The original checkout's
  README, ROADMAP, architecture, ECC plan and capability manifest overlays were
  hash-checked unchanged. Existing worktrees and unrelated files remain intact.
- No push, main merge, release, deployment, model download, hosted inference,
  public bind, private fixture, advisory-policy activation or modification of
  existing services/volumes was performed.

The earlier frozen candidate `3d8ba0e` passed its clean driver and image build but
was superseded after additional dialog contrast findings. Its receipts retain
that commit identity. They are preparation evidence, not a substitute for the
replacement candidate above.

## Implemented and repaired

- Preserved Milestone 1 documentation separately at `fbedf59` and the original
  Milestone 2 boundary fixes at `b2faedf`. Reverified H1 ownership/recovery at
  `33d87c8`: random worker/attempt identity, leases, repeated reconciliation,
  matching-resource repair and stale publication rejection.
- Added frozen synthetic development/holdout fixtures, deterministic scope,
  citation, origin, immutable-revision and lifecycle checks; repeat-run receipts;
  blinded review packets, blank forms and a scoring/import procedure. Human
  review provenance and disagreements remain separate from AI review.
- Reproduced duplicate root generation on lost-response replay and concurrent
  requests before fixing admission. Persistent request keys now retain one
  task/report identity, conflicting parameters return 409, and one active root
  request owns each simulation's generation resource. The frontend keeps its
  request key across transport retries. Replay history lasts while task rows remain.
- Fixed browser failures in responsive controls, keyboard upload, dialog focus,
  hidden panels, error/retry states, missing metrics and interrupted report
  controls. Open-dialog contrast received both automated and manual checks;
  Chromium's sandbox is explicitly enabled and attested in the final suites.
- Fresh review reproduced two additional H1 call-site failures: old preparation
  files falsely reported readiness, and expired ensemble cleanup could delete
  a replacement run. Both have fail-first regressions and independently repeated
  successful reproductions after repair. See [the review addendum](2026-10-02-h1-integration-review.md).
- Pinned container runtime image digests, froze Python resolution, and excluded
  runtime logs from build context. Added clean-install, real-storage and cold
  restore probes; README, ROADMAP, architecture, recovery and capability status
  now distinguish historical evidence, current source and remaining gaps.

## Assignments and local commits

All editing specialists started from `fbedf59752fbc3387e4aa164c2f6f5869d4744de`
in independently verified worktrees/gitdirs. Only the coordinator integrated
commits and edited shared milestone/capability documents. Heavy verification
was coordinated. Milestones 3–5 used explicit model substitutes; these checks
made no real generation calls.

| Owner | Assigned worktree | Specialist commits → integration commits |
| --- | --- | --- |
| A, evaluations | `crowdlens-ecc-eval` | `d815c6d → 7b4a99a`, `86f5882 → e5108ca`, `b809925 → 3710c5d`, `cba394e → 1b4d239` |
| B, browser QA | `crowdlens-ecc-browser` | `fb66abc → 5d82fe1`; test/sandbox corrections `9a8701f → 56368ed`, `6c766ba → bc1bf6c`, `5ca4390 → 3d8ba0e`; modal corrections `60888bf → f0059de`, `0a3911b → ebfd28d`, `dfc1fb6 → 242b899`; reporting `cdec5b2 → 1b2065a`, `67b12c4 → 0a7b0aa` |
| C, release verification | `crowdlens-ecc-release` | `a5368e8 → ab406d5`, `edbda23 → b79cd30`, `a436c5f → 203dc84`, `786510a → 665d6b0`, `6f3e0a3 → 05c86a6`; reporting `fb7ce19 → e0fe50b` |
| Coordinator | `crowdlens-ecc-integration` | H1 `33d87c8`; request admission `50e18a3`, `d021799`; review fixes `b5bbfac`, `c800a3d`; container inputs `5bbaa2d`, `8850b92`; separate evidence/docs commits |
| Fresh AI reviewer | Read-only combined checkout | No source edits; independent reproductions and 82-case guarded regression run, source/screenshot review and final receipt/claim review |

See the [task ledger](2026-10-02-ecc-execution-ledger.md) for dependencies,
isolation and preserved boundaries. AI code review is not independent human
factual adjudication of generated reports.

## Fresh verification of the frozen candidate

The clean run used its own checkout and freshly installed environments at
`/tmp/crowdlens-ecc-release-final-242b8999/source`, with Node **22.23.3**, npm
**10.9.9**, Python **3.11.15** and uv **0.9.26**. Installed environments were not
borrowed from any existing worktree. Lockfile hashes remained unchanged; the
checkout had no tracked or untracked changes. Installed dependencies, caches,
build output and synthetic runtime artifacts were ignored inputs, recorded
separately. The image build used a second clean checkout without those inputs.

| Check | Fresh result and boundary |
| --- | --- |
| Clean verification driver | All 26 commands returned 0: frozen installs, inventories, tests/build, audits, H1 process recovery, backup, evaluations, disposable Compose validation, identity and working-tree checks. Command arguments, environment policy, timings and log hashes are in the [release report](2026-10-02-milestone5-release-verification.md). |
| `UV_PYTHON=3.11 npm run check` | **449 backend + 12 Node + 20 Vitest tests passed (481 total)**; production Vite build passed. Backend discovery includes one script test beyond the 448 tests under `backend/tests/`. These totals include overlapping structural checks; do not add the evaluation count as new unique coverage. |
| Dependency checks | Both `npm audit` runs reported zero vulnerabilities at every severity. `uv pip check` found no incompatibilities among 146 installed packages; it is not a Python vulnerability scan. |
| H1 process recovery | A separate writer process exited; the production 30-second lease expired and polling restored the task as failed with `ownership_lease_expired` after 30.1 seconds. Guarded/API/multi-process tests also preserve valid replacement owners and reject stale publication. |
| Deterministic evaluations | **167/167 passed on each of three runs (501 test executions)**, no missing observations. First-attempt and three-run stability both 167/167. Corpus outcomes across the three runs: **15 ready, 30 intentionally blocked**, 54 scripted calls, zero real model calls. A correctly blocked safety assertion is not a successful draft. |
| Actual built UI | Workflow **10/10**, recovery/error-state suite **10/10**. Eighteen stage/width snapshots plus three open-dialog widths at 375/768/1440px; no detected axe violations or uncaught page errors. Each dialog width has 23 passing supplementary text-contrast checks, with axe incomplete entries retained. Chromium sandbox launch arguments/status are attested. |
| SQLite/artifact cold restore | **26 files** copied after writer exit, restored in a fresh process; immutable child and unchanged archived original verified. Same-root restore reconciled two expired owned tasks, failed their matching project/interrupted report, and preserved a valid newer lease/project. Controlled clock is disclosed; active-task relocation and online atomic backup are not covered. |
| Separate Neo4j cold restore | Synthetic graph dumped after shutdown and loaded into a new volume; restored graph checks and removal of the probe's four containers and three volumes passed. This is not a coordinated online cross-store backup. |
| Exact-candidate image build | Passed in 630.727 seconds from a clean context and frozen tree. Image **`sha256:9d9c9a37c6e892dacb74ca09fe7b3d55e1d5b3aa62e6f89f08b3b5f25929a253`**, size 13,794,839,834 bytes. Image Python is 3.11.17 versus host-check Python 3.11.15; both use Node 22.23.3 and uv 0.9.26. The existing `npm run dev` container command remains; production frontend compilation was verified separately. |
| Real HTTP/SQLite/Neo4j | Passed source/origin isolation, stale-owner Neo4j write rejection, preserved replacement generation, acceptance retry returning the same immutable child, unchanged parent hashes and reopened Needs review. Three scripted drafting calls; zero real model calls, semantic embeddings disabled. |
| Exact image startup | `/health`, `/api/status`, frontend `/` and frontend API proxy all returned 200 with the exact candidate revision/source fingerprint. SQLite and Neo4j were healthy; embeddings/vector search/full readiness correctly remained false with provider endpoints disabled. Probe containers/network were removed. This verifies startup and honest degraded readiness, not real inference. |
| Exact-candidate remote CI | Read-only GitHub queries returned **422 No commit found** for commit/check-runs and **zero Actions runs** for this local SHA. No push occurred. |

The [evaluation guide](../evaluations/evidence-quality.md) preserves the frozen
164-check before baseline (two duplicated-root failures on all three runs) and
matching after baseline (164/164 on all three). The later importer safeguards
bring the final selection to 167; old receipts keep their original counts and
commits. Fixture manifest SHA-256 remains
`78dc98ecd30ac22f14aa40c4ae8635145b43801f257af623f7d00abe89a5b12f`.
Provider latency, model cost, attribution accuracy, unsupported-claim rate,
omissions and human effort remain **unmeasured/null**. Four blinded packets and
blank forms are ready, with zero completed human reviews. ECC's optional runner
was not used to bypass its unavailable containment gate; the repository's native
guarded pytest harness provides the execution evidence.

The [browser report](2026-10-02-milestone4-browser-qa.md) identifies each
substitution: ontology/graph responses, seeded scenario/simulation data,
intercepted root generation and deterministic drafting. Actual Flask/SQLite
proposal acceptance, lost-response retry, stale conflict, immutable child reopen,
Needs review state, parent hashes and owned-task exit/manual retry were exercised.
Expected injected HTTP failures and browser warnings remain in the receipts;
this is not a zero-console-error claim. The displayed quality heuristic is not
a factual-accuracy score, and unavailable graph/elapsed values show Unknown.

The first image/service probe stopped before application startup because this
Docker host did not publish ports on the newly created internal network. A
separate cached-Python diagnostic reproduced that behavior and successful
loopback publication on a new ordinary bridge. The successful retry used a new
disposable bridge, only `127.0.0.1` host publications and disabled provider
endpoints. Initial failure, diagnosis, successful retry and cleanup receipts are
all retained; no application assertion or source was changed to pass the retry.
The startup container configuration snapshot SHA-256 is
`0e77b6c26bb9349ca71fe29cbdb641e47c07638f3552ef60e793f7ea41433ffc`.
Its inspected writable-layer artifacts are disclosed in the release report.
The built local images remain available for inspection; no test containers,
networks or volumes remain.

The coordinator inspected final-candidate source inspection at 375px, the history
dialog at 768px and the reopened revision at 1440px. B and the independent AI
reviewer inspected additional final screenshots and persisted identity/hash
receipts. This is the first visual baseline; historical visual-regression success
and exhaustive accessibility conformance are not established.

The fresh AI reviewer independently reproduced both backend findings before and
after repair, ran 82 guarded regression cases, examined the final source changes
and screenshots, and checked final clean-run/build/service log hashes. Its final
review verified all 141 release-manifest entries against preserved copies and
originals and found no unresolved confirmed source/evidence findings within this
scope. This is AI implementation review; human factual review remains blocked.

`git diff --check` on the clean verification checkout passed. The full
`main..242b899` check returned 2 for 35 whitespace warnings in eight byte-preserved
raw pytest/XML failure receipts. Source and maintained documentation pass the
scoped whitespace check. Raw historical receipts retain their original hashes;
the report does not claim a clean full-branch whitespace result.

Documentation-only integration preserves the tested runtime sources, tests,
dependencies and build configuration. Final documentation checks cover local
Markdown targets, JSON parsing, evidence manifests and original-overlay hashes;
their [receipt](evidence/2026-10-02-ecc-handoff/documentation-checks.json) records
the verified scope. The final chat names the resulting reporting HEAD separately.
No integration changes remain uncommitted after that reporting commit; the
primary checkout's five original documentation overlays remain intentionally
uncommitted and untouched.

## Separate completion statuses

| Workstream | Status | Supporting evidence and missing acceptance criteria |
| --- | --- | --- |
| H1 / Milestone 2 scoped remediation | **COMPLETE** | Existing boundary fixes preserved; ownership recovery, stale-owner fencing, repeat reconciliation, legacy uncertainty, valid-owner preservation, honest preparation and guarded ensemble cleanup verified. [H1](2026-10-02-h1-task-recovery.md), [root admission](2026-10-02-root-request-recovery.md), [independent repairs](2026-10-02-h1-integration-review.md). This does not complete OASIS continuation, lossless memory or whole-root budget policy. |
| Milestone 3 harness and deterministic baseline | **COMPLETE** | Versioned frozen fixtures, fail-first before/after receipts, structural/lifecycle assertions and three-repeat final results delivered; 501/501 test executions. No prompt tuning against holdouts. |
| Milestone 3 model-output and human-reviewed quality | **BLOCKED** | No suitable installed generation model or independent human labels. Ready-made scripted drafts establish structural behavior only; unmeasured quality/effort metrics remain null. |
| Milestone 4 browser coverage | **PARTIAL** | All bounded supported-state checks and scoped fixes pass on the combined built UI at three widths, including actual API recovery/revision persistence. The complete real generation/OASIS journey is blocked; historical visual comparison and exhaustive accessibility remain unverified. |
| Milestone 5 local release verification | **COMPLETE** | Applicable authorized local checks passed: clean installs, tests/build/audits, evaluations, browser suites, H1, real HTTP/Neo4j, cold restores and exact image startup with honest degraded readiness. No configured lint/type/coverage, Python/container vulnerability scan, real inference or production-serving verification is implied. |
| Exact-candidate remote CI | **NOT RUN** | Candidate remains local; exact-SHA queries find no commit/checks. Requires authorized push and a PR/main-triggered run, recording the actual checked-out SHA/tree. |
| Full real-service/model workflow | **BLOCKED** | Local inventory contains only `nomic-embed-text:latest`; no generation model. No actual extraction → graph → OASIS → report pipeline is claimed. |
| Existing deployment verification | **NOT RUN** | Existing deployment/services/volumes were left intact. Earlier read-only observations do not verify this candidate in that deployment. |

## Remaining actions and owners

| Boundary | Precise next action | Owner |
| --- | --- | --- |
| Real generation and full workflow | Supply the missing default `qwen2.5:32b` on an isolated Ollama-compatible endpoint (`LLM_DEFAULT_PROVIDER=ollama`, `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL_NAME=qwen2.5:32b` for host-local execution), or explicitly choose another already-installed suitable model ID and matching reachable endpoint. Downloads require separate authorization; the earlier H1 probe model `qwen2.5:3b` is also absent. Set bounded calls/runtime/resources and `EMBEDDING_AUTO_PULL=False`, then run the synthetic document through all real stages. Inventory contains only the embedding model. Hosted inference additionally needs explicit provider, permitted inputs and spending authorization. | Operator for model/authorization; implementation agent for bounded execution |
| Human-reviewed quality | Have independent human reviewers complete the four blinded packets with provenance and measured effort; import the forms, preserve disagreements and adjudicate before computing supported attribution/unsupported-claim/omission rates. Define any future thresholds before tuning. | Human reviewers and evaluation owner |
| Exact-candidate remote CI | Authorize pushing the reviewed branch and creating/updating a PR at the intended commit. CI triggers on main push or PR, not a feature-branch push alone. Record the actual checkout SHA/tree, check results and any PR merge-ref difference. Do not transfer old CI evidence to this candidate or the later documentation HEAD. | Operator authorization, then release owner |
| Deployment equivalence | Separately authorize backup and deployment reconciliation against the chosen revision; verify runtime fingerprint, image/configuration identity and current workflow routes after rollout. | Operator/deployment owner |
| Whole-root execution budget | Define aggregate call, cost and deadline behavior before implementing its acceptance criteria. The 1,530 simulated seconds in the transport fault probe is characterization, not measured latency or a passing budget policy. | Product/runtime owner |
| Persistence/operations | Define retention/deletion and coordinated backup points. Active-task relocation, online atomic cross-store backup, power-loss behavior, exact-round OASIS continuation and lossless agent memory remain unverified. | Product/storage owner |
| Broader verification | Add justified lint/type/coverage and Python/container vulnerability scanning; broaden browser/screen-reader and real graph-canvas checks; verify additional Python/runtime/model versions before promising them. Wire the CI image revision build argument before relying on its metadata. | Maintainers/release owner |

Structural success and synthetic browser/storage evidence do not establish factual
quality or forecast accuracy. No missing human/model measurement is reported as
zero error, and no seeded later stage is evidence that earlier real stages ran.
