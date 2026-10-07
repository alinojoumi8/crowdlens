# ECC Milestones 3–5 local execution ledger

Date: 2026-10-02. Coordinator: primary implementation agent.
Code baseline: `33d87c82c5f3ecb3435ba86a5160a44f79635443` (H1 repair).
Milestone 1 documentation overlays are preserved in a separate documentation commit.
Existing worktrees and the primary checkout remain intact. No push, main merge or deployment is authorized.

| Owner | Scope | Dependencies | Status | Integrated local commits | Evidence | Remaining boundary |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | H1, root request admission, cross-agent integration and shared docs | Original M2 audit | COMPLETE scoped implementation, integration and shared reporting | `33d87c8`, `50e18a3`, `d021799`, `b5bbfac`, `c800a3d`; build `5bbaa2d`, `8850b92` | [H1](2026-10-02-h1-task-recovery.md), [root retry](2026-10-02-root-request-recovery.md), [review fixes](2026-10-02-h1-integration-review.md) | Whole-root budget and deployment remain separate |
| Specialist A | Frozen synthetic evaluations and blinded review forms | H1 baseline; before baseline precedes root repair | COMPLETE deterministic harness; model/human quality BLOCKED | `7b4a99a`, `e5108ca`, `3710c5d`, `1b4d239` | [Evaluation guide](../evaluations/evidence-quality.md), retained before/after receipts | Suitable generation model and independent human labels absent |
| Specialist B | Built-UI QA, scoped frontend fixes, screenshots | H1 and combined candidate retest | PARTIAL overall coverage; all 20 bounded final-candidate checks pass | `5d82fe1`, `56368ed`, `bc1bf6c`, `3d8ba0e`, `f0059de`, `ebfd28d`, `242b899`; reporting `1b2065a`, `0a7b0aa` | [Browser QA](2026-10-02-milestone4-browser-qa.md) | Seeded/substituted generation stages do not establish real model E2E |
| Specialist C | Clean installs, tests, real storage, cold restore, image verification | Final frozen candidate | COMPLETE applicable authorized local verification | `ab406d5`, `b79cd30`, `203dc84`, `665d6b0`, `05c86a6`; reporting `e0fe50b` | [Release evidence](2026-10-02-milestone5-release-verification.md) | Exact-candidate remote CI needs authorized push and PR-triggered checks |
| Fresh AI reviewer | Combined code, regressions, screenshots and claims | Independent implementation complete | COMPLETE scoped source/evidence review; no unresolved confirmed findings | No source edits | 82 guarded tests; preserved independent reproductions; modal contrast review; final receipt/manifest/claim checks in handoff | AI code review is not human factual adjudication |

Only the coordinator integrates commits, resolves shared ownership, and edits the ECC plan/capability manifest. Each editing agent receives an isolated worktree. Temporary state and services must be separate; heavyweight builds are coordinated.

## Verified isolation and preparation

All three specialists independently confirmed clean `fbedf59` worktrees before editing:

- A: `codex/crowdlens-ecc-eval`, separate checkout `crowdlens-ecc-eval` and gitdir `mirofish-local3`.
- B: `codex/crowdlens-ecc-browser`, separate checkout `crowdlens-ecc-browser` and gitdir `mirofish-local4`.
- C: `codex/crowdlens-ecc-release`, separate checkout `crowdlens-ecc-release` and gitdir `mirofish-local5`.

The coordinator's `codex/crowdlens-ecc-integration` branch contains the separate
Milestone 1 overlay commit `fbedf59`. Existing primary and Milestone 2 checkouts
retain their own overlays. Graph project `crowdlens-ecc-integration` was indexed
from this source; scripts/documentation excluded by fast indexing are read directly.

Coordinator commit `5bbaa2d` pins official Node 22, Python 3.11 and uv 0.9.26
container image digests and freezes Python dependency resolution. Registry metadata
was verified; image execution is recorded separately for each frozen candidate. The original
Dockerfile issue is a source-confirmed reproducibility gap, not a claimed build failure.

Read-only local model inventory contains only `nomic-embed-text:latest`.
Real generation remains blocked; independent local checks continue.

## Integration sequence and evidence

- A froze corpus/assertions at `d815c6d` (integrated `7b4a99a`) before its baseline.
  Two root-admission fault tests failed unchanged on the coordinator's reproduction.
- Coordinator fixed root request replay/admission at `50e18a3`: 52 focused tests
  passed. An added real two-process test at `d021799` verifies one dispatch/task;
  all ten request-admission cases pass. The all-backend run before that extra test
  passed 403 tests. Final exact-candidate evidence is linked in the consolidated handoff.
- C's release/backup/real-storage probes `a5368e8` and `edbda23` were reviewed and
  integrated as `ab406d5` and `b79cd30`. Its earlier clean-install rehearsal is
  preparation evidence only; it does not verify the combined candidate.
- Whole-root call/cost/deadline policy remains an explicit operational gap.
  The transport probe's 1,530 simulated seconds is a retry-mechanism measurement;
  it does not establish a budget acceptance threshold or real model latency.

## Final handoff and preserved boundaries

See the [consolidated handoff](2026-10-02-ecc-milestones-3-5.md) for the final
candidate, reporting commit, separate completion statuses and next owners.
Earlier receipts keep their original commit identities; a superseded candidate's
checks are not relabeled as the final run. Chromium verification explicitly retains
its sandbox and records actual launch arguments and sandbox status.

The primary checkout's five original documentation overlays were hash-checked
unchanged, and `main` remains `34275b75223dee82087ff6ac937c4fc6e4af9323`.
The H1/Milestone 2, evaluation, browser, release and integration worktrees remain
available. Only disposable test state/services were created. No push, main merge,
release, deployment, model download, hosted inference, private fixture, public
bind or existing service/volume modification is part of this execution.
