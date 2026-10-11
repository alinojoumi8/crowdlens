# Recovery and retention verification — 2026-10-11

## Reproduced defects and fixes

Disposable pre-fix reproductions showed malformed memory being overwritten without
retaining its bytes, and a `..` project ID reaching the parent directory after
metadata deletion. The HTTP regression reproduced the latter using an encoded path
in a Flask test client. No existing user data was used. New regressions failed
before the fixes, then passed with quarantine/atomic memory writes and pre-mutation
project path validation.

A third defect allowed graph-memory duplicates when a later extraction step failed.
Stable per-batch memory IDs and idempotent Neo4j writes now cover both that retry and
an acknowledgement lost after a real commit. These IDs are not a restart replay
protocol and do not establish exactly-once text extraction.

## Offline validation

The full local check passed 952 backend tests, 95 frontend tests (12 Node + 83 Vue)
and production build. One additional unreadable-cache regression was then added
and verified with the 19-test memory suite. Committed-candidate CI is tracked by
the pull request; runtime deployment is a separate final gate.

Project tests cover invalid/absolute/traversal IDs, HTTP rejection, symlink roots,
filesystem failures retaining metadata, selected deletion and unrelated project,
case history, source, action-log and report preservation. Memory tests cover
truncation, invalid UTF-8, invalid nested data/non-finite JSON, preserved raw bytes,
failed quarantine, failed atomic replacement, invalid new state and unreadable
previous state. No hosted inference was performed.

## Owned real-Neo4j rehearsal

[Full receipt](evidence/2026-10-11-recovery-retention/neo4j-rehearsal.json).
The cached immutable Neo4j image ran in a new named container/volume on a
nondefault loopback port. The script refused existing output storage and prohibited
provider HTTP. Only its own graph service was stopped, restarted and removed.
Embedding vectors and text extraction were explicit substitutes.

- A real transaction committed before a synthetic lost acknowledgement; retry
  retained exactly one memory node.
- Two subsequent extraction failures caused three batch attempts but only one
  additional memory node. Successful accounting reported one sent item.
- With the container stopped, nested retries exhausted and reported one failed
  batch, zero items sent, and no later extraction calls. Partial report and action
  hashes remained unchanged.
- The same driver/storage instance reconnected after restart and successfully
  persisted/read a new ontology. Earlier graph content survived the outage.
- A Cypher-looking graph ID was treated as a parameter. Deleting the selected
  graph removed its nodes while the independent second graph's nodes, source
  content, properties and relationships remained byte-equivalent after JSON
  serialization. All retained filesystem hashes matched.
- The owned container and volume were removed successfully. Zero provider calls.

The tested runtime source fingerprint is
`775ca8a94420c6ca09dfb8c85b06ff1510c86b11324dd29c8dde551fa6acfec4`.
Driver transaction retry was disabled and storage backoff shortened for this
rehearsal. This is not evidence of production outage timing, lossless continuation,
cross-stage transactions, an online backup or independent factual quality.

The [retention contract](../recovery-retention.md) names retained stores and warns
that project deletion can leave historical original-source references missing.
No real project, case, graph or report was deleted by these tests.
