# H1 remediation: owned generic tasks and honest recovery

Date: 2026-10-02. Scope: the remaining H1 finding from the
[Milestone 2 audit](2026-10-02-milestone-2-agent-audit.md), using installed
ECC 2.2.3 `agent-architecture-audit` guidance. This addendum preserves the earlier
audit as historical evidence.

**H1 is fixed and verified in the isolated source.** The original two-process
failure now recovers through the background monitor. New ownership prevents late
status and output publication after expiry or replacement. Legacy tasks without
ownership remain explicitly uncertain. This is not a deployment or release verdict.

## Baseline and preserved work

Actual starting branch: `codex/crowdlens-milestone2`; HEAD `b2faedf`.
There were no intervening H1 commits. The five prior boundary fixes remained in
place. Original README, ROADMAP, architecture, ECC plan and capability manifest
were hashed before work and preserved byte-for-byte in the primary checkout.
The worktree retained its three tracked Milestone 1 documentation changes and
untracked plan/manifest overlays. Only appended H1 evidence/status changes in
those worktree overlays are attributable to this task; they remain outside the
focused repair commit.

Read the applicable AGENTS instructions, installed audit skill, original report,
and task/control-plane/recovery source. Graph discovery found task symbols and
four callers, while source additionally contained preparation, ensemble and
proposal dispatch; the index describes main rather than this worktree. Current
source and tests were authoritative for the complete dispatch inventory.

Final tested runtime-source fingerprint:
`7f14199ab48a04c4a99e25a5bfdea6933fb7a07c838ef90434809a82062d7a8f`
(`runtime-source-v1`, base `b2faedf` plus the repair). This fingerprint excludes
docs/tests/operator data and is not an attestation of a deployed image.

## Root cause and contract

The old task manager persisted status but had no execution ownership, lease or
conditional write. It also preferred its local cache over another worker's newer
state. Startup reconciled simulation runners only. A task writer could disappear
while `processing` and leave a project stuck in `graph_building` indefinitely.

The new [ownership runtime](../../backend/app/services/task_execution.py) defines:

- A fresh worker UUID and task-attempt UUID, plus diagnostic PID. A restart or
  reused PID cannot renew another worker's attempt. A fork cannot reuse its
  parent's runtime identity.
- A **30-second lease** and **five-second monitor interval**, shared by renewal
  and recovery. Renewal watches the actual registered execution thread. A required
  child that exits stops renewal until its result is consumed/unregistered.
- A cross-process lock associated with the SQLite database for ownership changes,
  publication and recovery. A token, current binding, active status and unexpired
  lease are checked before each protected publication. Lock acquisition orders a
  heartbeat, completion and recovery race; an expired attempt cannot renew itself.
- Resource bindings for graph projects, report IDs, simulation preparation,
  ensembles and proposals. A manual retry receives a new task/attempt and binding.
  A late old worker cannot replace the newer task's state or output.
- Failed state with persisted reason `ownership_lease_expired` after expiry, or
  `execution_worker_exited` when a managed execution exits unexpectedly. A managed
  function returning without a terminal result fails with
  `execution_ended_without_result`. These do not imply automatic continuation.
- A recoverable pending-repair record: mark the task first, apply only related
  writes still bound to the attempt, then acknowledge repair. Interrupted repairs
  repeat safely. A damaged related artifact leaves repair pending while other
  tasks can still recover. Admission to that damaged resource remains blocked.

The lease authorizes work; expiry does not prove process death. In normal local
storage conditions, abandonment is detected by lease expiry plus at most one
five-second monitor interval. Immediate managed-thread exit is recorded by its
wrapper. Task/project API reads and new admission also run reconciliation.
Storage stalls, scheduler delays and wall-clock adjustments can delay timing;
this is not a hard real-time guarantee.

## Changes at the workflow boundaries

[TaskManager](../../backend/app/models/task.py) now reads durable task state and
uses owned dispatch. [Control-plane startup](../../backend/app/services/control_plane.py)
starts periodic recovery. [SQLite schema 2](../../backend/app/storage/control_db.py)
adds resource bindings without rewriting or deleting legacy task data.

Graph build, standalone graph-builder tasks, root report generation/resume,
simulation preparation, ensemble execution and evidence-proposal workers all use
the dispatcher. Graph/profile thread-pool jobs carry the execution context.
Proposal watchdogs retain their exact task identity. Ensemble wait periods
register the actual child process so a live parent cannot renew a departed child.
Root report admission follows readiness preflight, avoiding tasks for refused
requests. Resource ownership does not deduplicate separate new root report IDs.

Fences cover task transitions, project/case updates, report metadata/sections/
progress/Markdown, simulation state/config/profiles, proposal content/snapshots,
Neo4j publication calls and ensemble output. Existing review/immutable revision
checks continue to apply. Provider usage telemetry remains appendable after
cancellation; it does not reopen an attempt or replace proposal content.

Recovery changes a project's still-building state only when its recorded task
ID and resource binding match the recovered attempt. A manual graph retry is then
admitted normally. Active or ownership-unknown builds cannot be force replaced.
Partial report metadata/progress becomes interrupted; completed, Needs review
and immutable reports are preserved. Sections/source artifacts are not deleted.
Preparation and active proposal state are repaired under their own bindings.

The [recovery documentation](../control-plane-migration.md) records the operator
contract. Memory-only configuration can detect local thread exit but cannot
persist tasks across process exit. Durable recovery requires SQLite.

## Before/after evidence

The requested baseline command, run unchanged at `b2faedf`, returned **1**:

```bash
backend/.venv/bin/python backend/scripts/probe_milestone2_task_restart.py
```

Task `749f4928-ea2b-4e11-a053-9e8aeff27c7d` remained `processing` after its writer
process exited. Four normal-suite contract tests were added before implementation;
that initial run had one failure and three setup errors because the ownership
implementation was absent. The existing reproduction established the behavioral
failure independently of those missing interfaces.

The probe now observes the production interval through a second process's
background monitor, reading storage directly so status polling cannot trigger
recovery. It returned **0** after **30.1 seconds** for task
`c0059faf-b365-48e2-853c-620387c62cb0`: `failed`, reason
`ownership_lease_expired`, `unresolved=false`. No service restart was involved.

[24 new normal-suite cases](../../backend/tests/test_task_ownership.py) cover:

| Boundary | Evidence |
| --- | --- |
| Process exit | Real task-writing subprocess exits; separate process recovers its persisted task with controlled lease timing. The standalone probe additionally checks real 30-second timing. |
| Live other worker | Actual second backend process remains alive and processing during repeated reconciliation, then completes successfully. |
| Thread/child exit | Managed thread raises SystemExit while backend remains alive. Separate test has a real child exit while its task parent stays alive; parent no longer renews ownership. |
| Restart/PID reuse | Same diagnostic PID with different worker UUID cannot renew old ownership. |
| Expiry and replacement | Old status writes, heartbeat, project publication, report sections, proposal content/snapshots and graph writes reject expired ownership. |
| Concurrent transitions | Deterministically ordered heartbeat/completion/expiry races through the real shared publication guard. Successful completion remains successful. |
| Interrupted recovery | Failure after the project write and between report metadata/progress writes; replay completes pending repair and cannot overwrite a newer binding. |
| Legacy and terminal state | Legacy ownership uncertainty remains; completed tasks, successful reports, Needs review and immutable revisions remain unchanged. Schema upgrade preserves legacy payloads. |
| API state/manual retry | Graph task AND project endpoints show failure after abandonment; a synthetic retry is admitted with a new ID. Delayed old project completion is rejected; active/unknown force replacement is refused. Dispatch is captured in this API test, with no graph or model call. |
| Continuing recovery | Monitor recovers without restart or API poll; one unrepairable file cannot block recovery of other expired tasks. |

## Commands and fresh results

| Category | Command / actual result |
| --- | --- |
| Focused regression/recovery | `.venv/bin/python -m pytest tests/test_task_ownership.py tests/test_evidence_proposals_api.py tests/test_report_revisions.py tests/test_control_db.py -q` from backend: **60 passed**. |
| Current repository checks | `UV_PYTHON=3.11 npm run check`: **391 backend + 12 Node + 16 component tests = 419 passed**; Vite production build passed. This is a fresh run, not the earlier 395-test result. |
| Existing reproduction | Before exit 1; after exit 0 via actual background recovery in 30.1 seconds, as recorded above. |
| Synthetic HTTP/Neo4j lifecycle | `PYTHONPATH=backend backend/.venv/bin/python backend/scripts/smoke_milestone2_boundaries.py --synthetic --neo4j-uri bolt://127.0.0.1:32771 --output-dir /tmp/crowdlens-h1-integration`: passed proposal creation/acceptance/retry, preserved parent and unselected section, and retained Needs review. |
| Real Neo4j write fence | `PYTHONPATH=backend backend/.venv/bin/python /tmp/crowdlens-h1-evidence/check_neo4j_fence.py`: passed. Real old attempt writes generation 1; new attempt writes generation 2; old attempt's delayed generation 99 write is rejected and database remains at 2. No inference. |
| Diff checks | `git diff --check` passed; Milestone 1 preservation and documentation link/name checks performed. |

The disposable Neo4j used cached 5.18 community image
`sha256:8f01f7bb053e5564eb84a3f1824e4ca2202d29dd415d196cf8e27c8f7e6b611e`,
loopback ports and tmpfs data/logs. It is separate from the existing deployment.
The proposal integration used actual HTTP, SQLite and Neo4j, with deterministic
drafting and disabled semantic embeddings explicitly substituted. It created
`proposal_ad48a91081f74374b32c320ce9cf864f` and child
`report_366fa808bd7342179b0e3d09b554ab9c` from `report_root` on HTTP port 38443.
One creation and three acceptance requests (stale digest, acceptance, retry)
preserved one child and unchanged parent/unselected content. That integration's
source fingerprint was
`53966506cf635497a17933f73beed5c89ad71f2470aef29eecdab7df7ebedfcf`;
final source subsequently restored the existing graph task display label and
removed a blank line. The final full suite and real Neo4j fence use the final
fingerprint recorded above.

The same bounded harness attempted one loopback-only upload/ontology request:
provider model-not-found 404, surfaced as API 500. Project
`proj_6e11a7e5b50f`; model `qwen2.5:3b`; one inference HTTP request, six-second
transport limit, zero hosted calls. No model was pulled. Graph → scenario →
simulation → report remains blocked as a full real-provider workflow.

Evidence receipts are under `/tmp/crowdlens-h1-evidence` and
`/tmp/crowdlens-h1-integration`; the companion JSON retains non-secret result
metadata. All fixtures/databases are synthetic. No private case documents or
reserved evaluations were used. The new disposable container was removed after
verification; existing services, data, volumes and configuration were untouched.

## Limits and separate verdicts

- **H1: fixed and verified locally** for new tasks participating in ownership.
  Legacy ownerless tasks remain flagged `ownership_unknown`, with a visible
  operator-review message and unchanged status. Their actual execution must be
  established before a separately reviewed manual repair; they are not swept.
- **Remaining Milestone 2 obligations:** deployed-source reconciliation and full
  workflow verification remain open. The original medium findings around root
  retries/aggregate budgets, runner PID reconciliation and memory durability
  remain follow-ups. This repair does not establish exact-round continuation,
  full backup/restore, power-loss durability or model quality.
- **Full workflow:** blocked by the unavailable local generation model. Passing
  deterministic lifecycle and real-storage checks do not establish report quality.
- **Deployment:** unchanged and not verified against this repair. The older image
  mismatch documented by the original audit remains unreconciled. No new image
  build, deployment, push, merge or fresh GitHub CI run is claimed here.

All cooperating writers must use this ownership protocol, a shared local control
DB/lock and stable artifact roots. Old application versions, external direct
writers and changing storage roots bypass that coordination. Loss of ownership
does not forcibly terminate already-issued provider/child work; late protected
publications are rejected. A storage call already admitted under the publication
lock precedes recovery; a stalled call can delay the next pass. Corrupt related
files remain preserved with repair pending. No release-readiness claim is made.
