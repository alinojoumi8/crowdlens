# SQLite control-plane migration

The control database stores small workflow records that need transactional
updates: projects, cases, tasks, and simulation run state. Neo4j remains the
knowledge-graph store, while documents, extracted text, caches, and other large
artifacts remain under `backend/uploads/`.

## First startup

CrowdLens retains legacy storage and Docker identifiers for compatibility; see
[the rebrand notes](rebranding.md). The default SQLite database lives under `backend/uploads/`; its exact path is
reported by `GET /api/status` and may be overridden with `CONTROL_DB_PATH`. On first startup the app
scans the existing `project.json`, `case.json`, and `run_state.json` records and
imports them in one SQLite transaction. Existing database rows win, so a retry
never overwrites newer durable state. After a successful import, a migration
marker prevents repeated scans.

Legacy JSON files are not deleted or rewritten by the import. Simulation
`run_state.json` files continue to be updated as compatibility mirrors for the
simulation subprocess IPC boundary. SQLite is authoritative for application
metadata after migration.

## Back up safely

Stop the application before copying the database so its WAL is fully
checkpointed, then copy the database and artifacts together:

```bash
cp -a backend/uploads /path/to/backup/
# If CONTROL_DB_PATH points outside uploads, copy that database as well.
```

For Docker, stop the application with `docker compose stop` first and back up the bind-mounted
`backend/uploads` directory. Neo4j data remains in its separate named volume and
needs its own backup strategy.

## Observe the migration

`GET /api/status` exposes:

- `control_db.healthy`, path, schema version, and journal mode;
- `control_db.migration`, including imported record counts;
- `control_db.runner_reconciliation`, including interrupted stale runs.

Application logs also record the database path and import counts at startup.

## Recover from a failed import

A malformed or unreadable legacy record prevents the migration marker from
being written. The app logs the exact file, leaves every source record intact,
and stops startup to prevent reads or writes against a stale filesystem snapshot.
Repair or restore the named JSON file and restart; the complete import will retry.

Do not delete legacy files immediately after migrating. They are a migration
snapshot, but they do not receive later project/case/task updates and therefore
are not a current rollback source. Back up the control database regularly once the app
has accepted new work.

## Generic task ownership and recovery (schema 2)

New tasks persist a random worker identity, a unique execution-attempt token,
heartbeat time and a 30-second ownership lease. PID is diagnostic information;
it is insufficient to renew or replace ownership. Existing task payloads survive
the additive schema upgrade, which introduces resource-to-attempt bindings.

A backend recovery monitor runs every five seconds. It renews only registered
execution threads that are alive and whose registered child workers are still
alive. An exited required child stops renewal even while its parent thread lives.
Expired leases become `failed` with `ownership_lease_expired`; lease expiry means
ownership expired, not proof that the process died. No automatic continuation is
attempted. Task/project reads and new admission also reconcile stale records.
Timing assumes functioning local storage and a consistent host clock; a blocked
storage operation can delay a recovery pass.

Ownership transitions and short publication operations share a process-safe
lock next to the SQLite file. Every task attempt must pass its token and lease
check before updating status or associated authoritative output. Recovery records
pending related repairs before applying them. It repeats unfinished repairs and
only changes resources still bound to that exact attempt. A failed repair remains
pending and does not prevent other tasks from being recovered.

For an abandoned graph build, only the matching project's still-building state
becomes failed, enabling an explicit manual retry. New active attempts and already
successful artifacts are preserved. Partial reports become interrupted; completed,
Needs review and immutable reports retain their artifacts. Proposal drafts and
simulation preparation state have corresponding guarded writes and recovery.

Legacy ownerless tasks retain their status and receive an `ownership_unknown`
reason and an operator-review message. Absence of ownership is not proof of
abandonment. A building project with active or unknown ownership cannot be force
replaced; its actual execution must be verified before a separate manual repair.
This does not retroactively make old workers participate in the protocol.

Durable recovery requires the configured SQLite control plane. Memory-only mode
can detect local execution-thread failure while the backend lives, but cannot
restore tasks after process exit. All cooperating workers must use this protocol
and stable storage paths; mixing old writers or externally editing database/files
bypasses its guarantees. Ongoing external calls are not forcibly cancelled by
losing ownership; their later publications are rejected.

See the [H1 remediation evidence](audits/2026-10-02-h1-task-recovery.md) for the
verified timing, subprocess tests, publication races and remaining limitations.

## Cold restore verification and limits

The [local release rehearsal](audits/2026-10-02-milestone5-release-verification.md)
copies a quiesced synthetic SQLite database and complete artifact roots, including
hidden proposal/lock files. Fresh processes reopen immutable revisions; restoring
at the same absolute roots also recovers expired tasks while preserving a newer
valid lease. Resource bindings store absolute paths, so moving active-task artifacts
to different roots is not supported by this evidence. A separate stopped Neo4j
dump/load rehearsal verifies synthetic nodes, relationships and properties in new
volumes. These are cold restores, not a coordinated online cross-store snapshot
or a power-loss durability test. No operator data or existing volume was modified.

[Integration review](audits/2026-10-02-h1-integration-review.md) also covers stale
preparation readiness and ensemble cleanup races. Serialized process-control calls
can delay heartbeat/recovery; the existing close IPC timeout is 20 seconds.
