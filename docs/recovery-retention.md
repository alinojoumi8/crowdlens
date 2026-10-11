# Optional memory recovery and scoped retention

## Damaged optional memory

`agent_short_memory.json` and `agent_memory_summaries.json` are optional caches,
not the original action log or a lossless continuation checkpoint. Loaders validate
UTF-8, JSON, agent/record shapes and the text/round fields used by runtime prompts.
Invalid files are ignored for context, with a warning. Exact damaged bytes are
preserved beside the file as `<filename>.corrupt-<sha256>` with private permissions.
The original stays untouched until a later valid save. If preservation or reading
fails, the save is skipped and a warning identifies the file; it is never silently
replaced with an empty cache. Valid saves use a flushed/fsynced temporary file in
the same directory followed by atomic replacement. Failed replacement retains the
last complete file and reports the failure.

Keep damaged copies and the original action logs in the coordinated backup.
Inspect warnings in `simulation.log` and the cache directory before authorizing a
restart. Restoring a known-good cache is an operator decision after writers stop;
do not infer missing events or treat the remaining cache as complete. There is no
automatic quarantine purge. Atomic replacement protects an individual JSON file;
it does not establish power-loss durability, cross-file transactions or lossless
concurrent read/modify/write across multiple simulation processes.

## Optional graph-memory outage

Graph writes use the existing bounded retry counts. Each updater batch now assigns
stable memory IDs before retrying. The memory write uses an idempotent Neo4j MERGE,
so a lost commit acknowledgement or a failed later extraction step does not create
another copy of that batch's memory records. The later text-extraction/episode
stage is not a cross-stage transaction; no exactly-once claim is made for it.

After retry exhaustion, updater statistics report a failed batch and logs record
the error; it is not counted as sent. Source files, local action logs and partial
report sections remain available. Failed batches are not automatically replayed
after a restart, and their ephemeral IDs are not a durable event replay protocol.
Stop or an exhausted allowance escapes retries through the existing WorkflowHalt
control. Recovery does not authorize additional generation. Operator review and
an explicit new allowance are required before replaying source actions.

The disposable rehearsal verifies a stopped/restarted Neo4j using the same driver,
then a successful write, without changing the shared database. Its connection
limits and shortened backoff are test settings, not production latency evidence.
Embeddings and extraction are scripted, so this does not measure memory/retrieval
quality or provider behavior.

## Deletion ownership and retained stores

Take a coordinated backup and stop affected writers before operator deletion.
The existing delete endpoints have separate, narrow scopes:

| Operation | Removed | Retained |
| --- | --- | --- |
| `DELETE /api/graph/project/{project_id}` | Selected project directory (original uploads, extracted text and per-document cache) and its project metadata row. | Case/version history, graph data, simulations/action logs, reports/revisions, proposal/review stores and workflow accounting. Other project files and metadata remain unchanged. |
| `DELETE /api/graph/delete/{graph_id}` | Neo4j nodes bearing the selected graph ID and relationships incident to those nodes. | Other independent graphs, SQLite metadata and all filesystem artifacts. |
| Report deletion | Governed by existing report/proposal ownership locks and tombstone contract. | No general project/case/graph purge is implied. |

Project IDs must be single valid path components. Project-root symlinks and paths
outside configured project storage are rejected with HTTP 400 before any database
or filesystem deletion. A filesystem deletion error returns HTTP 503 and leaves
project metadata available for recovery/retry. Successful deletion is logged with
the retained-store boundary. Missing projects return HTTP 404.

A case version stores references to project files, not another original-source
copy. Deleting that project can therefore leave historical source paths missing.
Keep the backup if those reports/case versions must remain independently
reviewable. Retained graph/source text is not a replacement for original bytes.
Do not interpret project deletion as removal of all copies of a case: exports,
backups, graph copies and review records follow their own retention decision.
There is no supported universal case cascade or automatic retention schedule.

Filesystem deletion and SQLite metadata removal are not one transaction. Removing
files precedes metadata removal so a disk failure does not discard the metadata;
a partial directory deletion or subsequent database failure still needs manual
recovery from the backup. Deletion is not safe against concurrent authorized
writers or adversarial changes to the configured storage root. Record the selected
IDs, backup receipt, operator decision, retained stores and verification result in
the private operational record. Never run blanket filesystem cleanup or unscoped
Cypher against an existing project.

See [cold backup/restore](coordinated-backup.md) and the
[verification receipt](audits/2026-10-11-recovery-retention.md).
