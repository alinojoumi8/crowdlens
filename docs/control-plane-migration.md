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
