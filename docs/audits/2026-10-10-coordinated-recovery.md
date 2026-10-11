# Coordinated cold recovery verification

Verified on October 10, 2026 (America/Toronto), using implementation commit
`8893cf3147bc06014f48a39f9985b61431b873e6`. Later documentation-only changes do not
alter this runtime source fingerprint:
`c970063c95456de32afc08469c1b8648bc1f0a25548923d0726e28e69c5db426`.

The application image was
`sha256:3ebd0a8a5b9db2b412bbc468a6def4c9dae10a7b3ce054f00ad046ac2a69339a`;
the cached Neo4j image was
`sha256:8f01f7bb053e5564eb84a3f1824e4ca2202d29dd415d196cf8e27c8f7e6b611e`.
The harness checked the application image's revision and source fingerprint
against the checkout before starting. Offline image smoke independently passed
non-root startup, built assets, graceful shutdown and persisted restart.

## Observed results

| Check | Result |
| --- | --- |
| Full backend suite | 887 passed |
| Frontend checks | 92 tests and production build passed |
| Coordinated backup and fresh-target restore | 29 files, including the graph dump; all SHA-256 checks matched |
| SQLite | Both databases passed integrity checks on disposable copies |
| Human review | Frozen packet identity, saved labels and pending values preserved |
| Reports | Immutable original and accepted-revision hashes preserved |
| Neo4j | Four nodes, two relationships and every property matched after offline dump/load |
| Cross-store links | Graph source, revision, proposal digest and review-packet identity matched |
| Task recovery | Two expired tasks recovered at their original absolute root; a newer valid lease was retained |
| Original snapshot | Unchanged after restore and recovery |
| Cleanup | All rehearsal-owned containers and volumes removed |
| Provider generation | Zero real model calls; drafting used three scripted fixture calls |

The implementation tests also exercise PID reuse, unavailable/legacy process
identity, database and compatibility-mirror write failures, active-owner fences
and a racing newer completion. Reconciliation never signals an unowned process.

## Reproduction and retained evidence

With the matching checkout, Python 3.11 environment and both images already
cached, use a new temporary directory:

```bash
UV_PYTHON=3.11 uv run --project backend python backend/scripts/check_ecc_neo4j_backup.py \
  --synthetic --coordinated \
  --image sha256:8f01f7bb053e5564eb84a3f1824e4ca2202d29dd415d196cf8e27c8f7e6b611e \
  --app-image sha256:3ebd0a8a5b9db2b412bbc468a6def4c9dae10a7b3ce054f00ad046ac2a69339a \
  --revision 8893cf3147bc06014f48a39f9985b61431b873e6 \
  --output-dir /tmp/NEW_CROWDLENS_REHEARSAL
```

The receipt, command logs, original fixture, bundle and restored artifacts are
retained privately under the delivery receipt's `coordinated-recovery` directory.
Bundle ID: `ccd6da6f-0ef4-4fdd-8976-75235a1d7e79`.
Dump SHA-256: `e17c4e6629584169ccba88d355e35fe7b79c38e778e7033534d728685ce80814`.

This is a cold, synthetic, explicitly quiesced restore. It does not establish
online atomic backup, power-loss durability, safe active-task relocation,
lossless simulation continuation or independently rated model quality. Existing
Neo4j/Ollama services and operator documents were not used or stopped. See the
[operator runbook](../coordinated-backup.md) for ownership, restore order and
manual retry boundaries.
