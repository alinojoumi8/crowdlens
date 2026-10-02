# ECC Milestones 3–5 local execution ledger

Date: 2026-10-02. Coordinator: primary implementation agent.
Code baseline: `33d87c82c5f3ecb3435ba86a5160a44f79635443` (H1 repair).
Milestone 1 documentation overlays are preserved in a separate documentation commit.
Existing worktrees and the primary checkout remain intact. No push, main merge or deployment is authorized.

| Owner | Scope | Dependencies | Status | Commits | Evidence | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | H1 recovery and boundary preservation | Milestone 2 `b2faedf` | COMPLETE locally | `33d87c8` | [H1 report](2026-10-02-h1-task-recovery.md); fresh 60-test regression rerun | Existing deployment and real model workflow separate |
| Specialist A | Versioned synthetic evaluations and review packets | H1 baseline | In progress | Pending | Pending | Real model and human labels unavailable until verified |
| Specialist B | Isolated built-UI QA and scoped frontend fixes | H1 baseline; combined candidate retest | In progress | Pending | Pending | Full model workflow prerequisites |
| Specialist C | Clean-environment preparation and final release verification | Frozen combined candidate for final checks | In progress | Pending | Pending | Exact-candidate remote CI requires a later authorized push |
| Fresh AI reviewer | Combined diff and claims review | Integrated implementation | Pending | N/A | Pending | Slot freed after implementation |

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
was verified; image execution awaits the frozen combined candidate. The original
Dockerfile issue is a source-confirmed reproducibility gap, not a claimed build failure.

Read-only local model inventory contains only `nomic-embed-text:latest`.
Real generation remains blocked; independent local checks continue.

## Integration evidence so far

- A froze corpus/assertions at `d815c6d` (integrated `7b4a99a`) before its baseline.
  Two root-admission fault tests failed unchanged on the coordinator's reproduction.
- Coordinator fixed root request replay/admission at `50e18a3`: 52 focused tests
  passed. An added real two-process test at `d021799` verifies one dispatch/task;
  all ten request-admission cases pass. The all-backend run before that extra test
  passed 403 tests. Final combined verification remains outstanding.
- C's release/backup/real-storage probes `a5368e8` and `edbda23` were reviewed and
  integrated as `ab406d5` and `b79cd30`. Its earlier clean-install rehearsal is
  preparation evidence only; it does not verify the combined candidate.
- Whole-root call/cost/deadline policy remains an explicit operational gap.
  The transport probe's 1,530 simulated seconds is a retry-mechanism measurement;
  it does not establish a budget acceptance threshold or real model latency.
