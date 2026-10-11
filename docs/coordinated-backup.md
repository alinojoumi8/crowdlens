# Coordinated cold backup and recovery

A usable backup must describe one quiesced set of application files, SQLite
state and Neo4j data. A case version is not a graph snapshot. This procedure does
not promise online atomicity, lossless worker continuation or power-loss recovery.
Keep backups private; reports, source files and database rows can be sensitive.

## Ownership and stop order

1. Identify the app image ID/revision, Neo4j image ID/database, all configured
   host/container roots, the app UID/GID, and every writer to the graph.
   Preserve private configuration and credentials separately with restricted
   access. A manifest is not a substitute for secrets needed to restore.
2. Stop new work; record active tasks and in-flight calls. Stop the application
   gracefully and verify its workers have exited. Stop prevents later admission;
   a previously sent provider request may still finish or be billed.
3. Coordinate with every Neo4j owner. Only its owner may stop a shared service.
   Do not run an unqualified `docker compose stop` on a shared host. With all
   graph writers quiesced, stop the selected database/service and produce a
   [Neo4j offline dump](https://neo4j.com/docs/operations-manual/current/backup-restore/offline-backup/)
   using its compatible image. Record the stop/dump evidence. The application
   must remain stopped throughout the dump and artifact copy.
4. Record quiescence in a private JSON receipt. The bundle tool checks this
   attestation and detects concurrent copy changes; it cannot prove that every
   external writer really stopped. Exclusive graph ownership means every writer
   to that database was coordinated, not that CrowdLens owns a shared host.

```json
{
  "application_writers_stopped": true,
  "neo4j_stopped_during_dump": true,
  "exclusive_graph_ownership": true,
  "observed_at": "REPLACE_WITH_ACTUAL_UTC_TIME",
  "note": "Identify stopped units, exited workers, dump and ownership evidence."
}
```

## Store inventory and bundle

Include the **entire uploads root**, hidden directories included. It normally
contains the control database, workflow/attempt accounting, sources/extracted
text, caches, simulation state/platform databases/action logs and memory files,
reports/revisions, private proposals, locks/tombstones and
`.human-reviews.sqlite3`. Include SQLite `-wal`, `-shm` and `-journal` sidecars
when present. Include external report, simulation, cache or database directories
as separately named roots. Keep service logs and configuration in the private
incident/backup record. Neo4j dumps include graph/source/vector/memory content;
Ollama models can be re-provisioned from recorded model/digest configuration.

```bash
# Run only after the recorded writers have stopped. Use actual immutable IDs.
backend/.venv/bin/python backend/scripts/cold_backup_bundle.py create \
  --root uploads=/absolute/uploads \
  --neo4j-dump /private/offline-dump/neo4j.dump \
  --revision FULL_GIT_SHA --app-image sha256:APP_IMAGE_ID \
  --neo4j-image sha256:NEO4J_IMAGE_ID \
  --quiescence-receipt /private/quiescence.json --output /private/NEW_BACKUP
backend/.venv/bin/python backend/scripts/cold_backup_bundle.py verify /private/NEW_BACKUP
```

Repeat `--root name=/directory` for external stores. The tool refuses symlinks,
source/destination overlap and existing destinations. SHA-256 covers every file;
original paths, UID/GID/modes and immutable image/revision identifiers are retained.
SQLite integrity checks run on disposable copies so the backup stays unchanged.
A failed copy has no completed manifest; preserve it for diagnosis and use a new
output path after resolving the failure. Checksums detect accidental changes;
they do not authenticate a maliciously rewritten manifest.

## Restore order

1. Verify the bundle, keep its original untouched, and restore into a **new**
   directory. The tool refuses to overwrite any existing destination:

   ```bash
   backend/.venv/bin/python backend/scripts/cold_backup_bundle.py restore-artifacts \
     /private/NEW_BACKUP --output /private/NEW_RESTORE
   ```

2. Load the copied `neo4j.dump` into a new empty Neo4j volume with the recorded
   compatible image. Verify graph/source relationships and vector metadata before
   selecting it as the app's graph store. Never load over a shared live database.
3. Map `stores/<name>` to the original configured application paths. Restore
   UID/GID/modes from the manifest as needed for the non-root app user. Retain
   original container paths: task-resource ownership stores absolute paths.
   Relocation of active-task state is unsupported; completed-artifact inspection
   in a disposable path does not establish safe active-task relocation.
4. Restore private configuration separately and start the recorded app image.
   Keep generation unauthorized. Verify SQLite integrity, original and revision
   hashes, review packet identity/history, task reconciliation, graph references,
   disk readiness and runtime source identity before reopening work.
5. Review interrupted/unknown work manually. Expired owned tasks become failed
   or interrupted and retain partial output; newer valid leases are preserved.
   Linux simulations retain PID, boot ID, process start ticks and PID namespace.
   Reused PIDs cannot establish a surviving worker. Legacy/unsupported process
   identities remain ownership-unknown and are never signalled by reconciliation.
   A retry requires explicit authorization; restore/polling does not supply it.

SQLite is authoritative for runner state. A database write failure leaves the
old compatibility mirror; a subsequent mirror replacement failure can leave a
newer committed database row with an older complete JSON mirror. Recovery reads
the database, preserves the old mirror until a successful write, and reports the
failure. This is not a cross-file transaction.

## Disposable verification

`check_ecc_neo4j_backup.py --synthetic --coordinated --image sha256:NEO4J_ID
--app-image sha256:APP_ID --revision FULL_SHA --output-dir /tmp/NEW_REHEARSAL`
uses cached immutable images, verifies the app image against checkout source,
seeds fictional original/revision/review artifacts and linked graph records,
stops its owned graph, bundles everything, then restores into new directories
and volumes. It compares hashes, hidden review labels, graph-to-artifact links
and database integrity, then tests expired-worker recovery at the original
absolute root. A fresh valid lease and archived original remain unchanged.
Only rehearsal-owned containers/volumes are removed. Existing services, operator
files and provider generation are not used.

For damaged optional memory, scoped deletion and retained-store decisions, see
[recovery and retention](recovery-retention.md). Quarantined memory copies remain
part of the private backup; project deletion is not a complete case purge.
