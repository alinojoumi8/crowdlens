# CrowdLens Milestone 5 release verification

Date: 2026-10-02. **Local synthetic verification passed; release readiness remains partial.**
Release-verification specialist C owns this evidence. The coordinator owns the
overall milestone assessment and integration decision.

The locally tested code candidate is
`242b8999044e33c8c3217df857c06401f3efbba3`, tree
`39753400064fe764b98152c2c0204005f874a9c1`. Later reporting-only commits must not be
relabeled as this tested code. Local structural verification does not establish
real-model quality, human acceptance, remote CI or an existing deployment.

Method: ECC 2.2.3 `verification-loop` and `production-audit`, adapted to the
repository's pytest, Node, Vitest, Vite, npm audit and Docker checks. Discovery
used the integration knowledge graph; actual source and fresh execution are the
authority. Existing services, operator data and deployments were unchanged.

## Identity, isolation and dependencies

The release worktree is
`/home/ali/.codex/worktrees/crowdlens-ecc-release/mirofish-local`, branch
`codex/crowdlens-ecc-release`, originally clean at
`fbedf59752fbc3387e4aa164c2f6f5869d4744de`. Its private gitdir is
`/home/ali/Documents/myprojects/mirofish-local/.git/worktrees/mirofish-local5`.
The inherited H1 baseline is `33d87c82c5f3ecb3435ba86a5160a44f79635443`.

Fresh final verification ran in
`/tmp/crowdlens-ecc-release-final-242b8999/source`. A separate clean checkout at
`/tmp/crowdlens-ecc-release-final-242b8999/image-source` supplied the image build
context. No installed environment was copied. Root/frontend `npm ci` and
`uv sync --frozen --dev` used the committed locks unchanged. Dependency download
caches were reusable; installed `.venv` and `node_modules` were new.

Runtime-source-v1 fingerprint:
`a807c651b35560c12a91ec6f0b79b2d32df7bad60ebf3322d121c643d9e835fb`.
Both browser harnesses independently report the same commit and fingerprint.
Local tooling was Node 22.23.3, npm 10.9.9, CPython 3.11.15 and CI-pinned uv
0.9.26. The Node tarball was verified against its official checksum; isolated
browser tools were exactly `playwright-core@1.55.1` and `axe-core@4.10.3`, with
system Chrome 154.0.8037.92. Python's 146 installed packages passed compatibility
checks; this is not a Python CVE scan.

| Frozen input | SHA-256 before and after |
| --- | --- |
| `package-lock.json` | `5fdcf1a09ef8beb772ed5bf2c849daab5852183cacfd81a8187f3a7fcbae7fa2` |
| `frontend/package-lock.json` | `bbbcf6412b694fe8bb25c56dd4c3e8b718ea1c01777efbc6131a0cdc146d8bf3` |
| `backend/uv.lock` | `1d6b2f50ff5b7dc57a9be10b3852f919d93e82cd8f862856b7e8d2581f92d88a` |

Tracked and ordinary untracked input state was clean before and after the
checks. Ignored outputs are explicitly inventoried: new environments, frontend
build, pytest/Python caches and backend logs. Docker context exclusions cover
these, `.env` and uploads. The separate image context had no ignored runtime
inputs. No operator `.env` was loaded; Compose used a disposable synthetic file.

## Final candidate results

All commands, exit codes, timings, original log paths and hashes are in the
[clean-run receipt](evidence/2026-10-02-release-verification/242b8999/receipt.json)
and the [preserved-file manifest](evidence/2026-10-02-release-verification/242b8999/preserved-files.json).
Original runtime outputs remain beneath
`/tmp/crowdlens-ecc-release-final-242b8999/`; copied receipts preserve their bytes.

| Check | Result and scope |
| --- | --- |
| `UV_PYTHON=3.11 npm run check` | PASS: 449 backend, 12 Node and 20 component tests; Vite production build. The backend-wide command includes 448 `tests/` cases plus `scripts/test_profile_format.py::test_profile_formats`. |
| Root and frontend `npm audit --audit-level=moderate --json` | PASS: zero reported vulnerabilities in each audit. |
| `uv pip check` | PASS: all installed dependencies compatible. |
| Frozen evaluator, three repeats | PASS: 167 structural tests per run, 501 executions, unchanged frozen corpus/inputs. Scripted model answers; no measured generation-model quality. |
| H1 two-process restart probe | PASS: exited writer, expired owned task failed in 30.10 real seconds with `ownership_lease_expired`. |
| SQLite and artifact backup/restore | PASS: quiesced 26-file snapshot, fresh-process terminal reopen and same-root active-task recovery. |
| Cold Neo4j dump/load | PASS: two nodes, one relationship and every fixture property retained; all owned temporary resources removed. |
| Browser workflow and recovery | PASS: two independently seeded suites, 10/10 checks each, sandboxed Chrome. |
| Responsive/accessibility samples | PASS: 18 workflow views and three history-modal sizes at 375/768/1440 px, zero detected axe violations; 23 modal text nodes per width satisfy measured contrast thresholds. |
| Synthetic Compose render | PASS: disposable configuration only; no service deployment. |
| Working-tree `git diff --check` | PASS with unchanged tracked and ordinary untracked inputs. |
| Full branch-range whitespace diagnostic | Known non-code warning: exit 2, 35 trailing-whitespace diagnostics in eight preserved raw fail-first pytest/XML receipts. Original bytes/hashes retained. |
| Real HTTP/SQLite/Neo4j revisions and fencing | PASS: source scope/origin isolation, stale graph-owner rejection, immutable revision reopen and idempotent acceptance. Three scripted model calls; zero real inference. |
| Exact-candidate image build/startup | PASS: pinned image built in 630.727 seconds; backend, frontend and API proxy return 200 with matching revision/source identity. SQLite and Neo4j healthy; embedding/vector/full readiness explicitly false. |
| Exact-candidate remote CI | NOT RUN: GitHub exact-SHA lookup/check-runs return 422 (commit not found); Actions query returns zero runs. |
| Real generation workflow | BLOCKED: no suitable generation model installed. |
| Python and container CVE scans | NOT RUN; npm audits and Python compatibility checks do not cover these. |
| Independent human quality/review effort | PENDING: zero completed reviewer forms; quality values remain null. |
| Existing deployment reconciliation | NOT RUN; outside this local verification scope. |

The [evaluation results](evidence/2026-10-02-release-verification/242b8999/evaluations/results.json)
keep model-support, omission, factual accuracy and human-effort claims separate
from structural behavior. The measured root transport mechanism can consume
five 300-second attempts plus 30 seconds of backoff (1,530 simulated seconds)
for one Anthropic call. No total-root elapsed-time/call/cost policy currently
exists; this is characterization, not failure against an invented limit.

The branch diagnostic compares main `34275b75223dee82087ff6ac937c4fc6e4af9323`
with the code candidate. Warnings occur only in the original evaluation
`2026-10-02-before/run-*.txt/xml` and reviewer `preparation-before.xml` /
`ensemble-before.xml` receipts. It is not an unqualified whole-branch diff pass.
The diagnostics are [retained](evidence/2026-10-02-release-verification/242b8999/raw/branch-diff-check.txt).
The reporting-only evidence addition itself retains 144 whitespace diagnostics
in six raw logs (including the original whitespace diagnostic output, failed
Neo4j setup and browser/build/startup logs). These bytes are not normalized;
report prose and structured metadata have no whitespace errors.

## Browser evidence

[Workflow results](evidence/2026-10-02-release-verification/242b8999/browser-workflow-results.json)
and [regression results](evidence/2026-10-02-release-verification/242b8999/browser-regressions-results.json)
record actual Chromium arguments and `chrome://sandbox`: PID/network namespaces
and Seccomp-BPF are enabled, with no `--no-sandbox` argument. Both suites have
zero uncaught page errors. Expected 409/503/lost-response faults, a synthetic
unimplemented diagnostics endpoint and preload warnings remain in the receipts;
this is not a claim of an empty console or universal accessibility certification.
Axe incomplete findings are retained, including gradients, non-text glyphs and
obscured background content. Modal text contrast is additionally measured.

The workflow uses real upload/project/task/report/proposal persistence while
ontology, graph, simulation and drafting responses are deterministic substitutes.
It verifies source inspection, conflict handling, unsupported proposal blocking,
idempotent acceptance, immutable child reload and history states. The recovery
suite exercises an actual exited task-owner process, visible failure and manual
retry. No generation provider is called.

Representative final screenshots were visually inspected at all three widths,
including every final history-modal size; B independently inspected additional
source/revision/proposal images. Preserved examples include
[mobile home](evidence/2026-10-02-release-verification/242b8999/screenshots/home-375.png),
[tablet source inspection](evidence/2026-10-02-release-verification/242b8999/screenshots/source-inspection-768.png),
[desktop saved revision](evidence/2026-10-02-release-verification/242b8999/screenshots/saved-revision-1440.png)
and the [mobile history modal](evidence/2026-10-02-release-verification/242b8999/screenshots/history-dialog-375.png).

## Recovery and image boundaries

The [SQLite/artifact receipt](evidence/2026-10-02-release-verification/242b8999/backup-result.json)
includes hidden proposal and lock files. At the same original absolute root,
fresh-process reconciliation fails two expired tasks, repairs their project and
partial report, preserves a valid-lease newer task/project and an immutable
Needs review revision, and makes no further changes on repetition. Archived
original and backup hashes remain unchanged. Controlled lease timing in this
probe is separate from the real-time H1 probe.

The [Neo4j receipt](evidence/2026-10-02-release-verification/242b8999/neo4j-backup-result.json)
uses cached community image
`sha256:8f01f7bb053e5564eb84a3f1824e4ca2202d29dd415d196cf8e27c8f7e6b611e`.
The writer stops before dump; an offline load creates a different new volume.
Dump SHA-256 is `2daee08f01b82ed5afc685a47dba9527f564ff79270fa0f4a2a67a6749f4d336`;
restored graph SHA-256 is
`2d05f29c3e42a645825e051b1df1011ef6b67b59d5cb185288f94bb12c8fc87f`.
These are separate stopped-component restores. Active task relocation, hot
coordinated snapshots and power-loss durability remain unverified.

Source-confirmed Docker reproducibility gaps in H1 were floating distro
Node/npm, floating base tags and non-frozen `uv sync`; no original build failure
is invented. The coordinator replaced them with pinned Node 22/bookworm,
Python 3.11/bookworm and uv 0.9.26 image digests and frozen synchronization.
The runtime command remains `npm run dev`. The production frontend build is
separately checked; the image does not claim static production serving.

The [exact image build](evidence/2026-10-02-release-verification/242b8999/image-build-receipt.json)
produced `sha256:9d9c9a37c6e892dacb74ca09fe7b3d55e1d5b3aa62e6f89f08b3b5f25929a253`
(13,794,839,834 reported bytes). Image Node is 22.23.3, Python is 3.11.17 and uv
is 0.9.26; the host test environment used Python 3.11.15, explicitly a different
patch version of the CI-selected 3.11 major. Image dependency compatibility
also passed for 146 packages.

The [real HTTP probe](evidence/2026-10-02-release-verification/242b8999/services-result.json)
ran against a new empty Neo4j database, verified source isolation and rejection
of stale generation 99 after current generation 2, and preserved original and
unselected content through acceptance, retry and Needs review reopen.

The [image startup receipt](evidence/2026-10-02-release-verification/242b8999/services-image-receipt.json)
records `/health`, `/api/status`, frontend `/` and its `/api/status` proxy returning
200 on loopback ports. Declared revision and source fingerprint match the host.
SQLite and Neo4j are healthy; disabled embedding endpoints correctly produce
`healthy=false` and `vector_search_usable=false`. `llm.configured=true` only means
a nonempty synthetic key was supplied; it is not an inference readiness probe.

The full synthetic container configuration snapshot has SHA-256
`0e77b6c26bb9349ca71fe29cbdb641e47c07638f3552ef60e793f7ea41433ffc`.
[Docker inspection](evidence/2026-10-02-release-verification/242b8999/raw/image-runtime-inspect.txt)
and [writable-layer changes](evidence/2026-10-02-release-verification/242b8999/raw/image-runtime-diff.txt)
preserve actual environment, loopback bindings, resource limits and generated
uv/editable-package, Vite/Python cache, log and upload state. Model URLs point to
disabled container loopback endpoints and `EMBEDDING_AUTO_PULL=False`. No private
uploads or existing service data were mounted.

The first startup attempt stopped before application checks because an internal
Docker test network exposed no published port. The same behavior reproduced
with a cached Python container after a two-second wait, while an ordinary fresh
bridge exposed the requested loopback port. This is a verified test-network
setup limitation, not an application failure or an inferred startup race.
[Original failed attempt](evidence/2026-10-02-release-verification/242b8999/services-image-attempt1/receipt.json)
and [independent diagnostic](evidence/2026-10-02-release-verification/242b8999/network-publication-diagnostic/receipt.json)
are retained. The successful attempt used a new bridge and only loopback host
publications. No existing network was changed.

The startup receipt's `phase` field is an earlier progress marker retained
verbatim; its final `status`, completed checks and cleanup fields establish the
completed result. All owned test containers, networks and volumes were removed,
and [post-runtime verification](evidence/2026-10-02-release-verification/242b8999/post-runtime-state.json)
found none remaining and a clean source checkout. The local built images remain
available for inspection; neither was deployed.

## Reproducible verification tools

- [Clean candidate runner](../../scripts/verify_ecc_release.py) clones an exact
  commit into a new temporary checkout, installs root/frontend dependencies with
  `npm ci` and Python dependencies with `uv sync --frozen --dev`, records installed
  versions and lock hashes, and runs the repository checks, audits, H1 process
  probe, backup rehearsal, evaluation runner, synthetic Compose validation and
  source/diff/working-tree checks. No existing `.venv` or `node_modules` is copied.
- [SQLite and artifact rehearsal](../../backend/scripts/check_ecc_backup.py)
  restores terminal revisions into a fresh process, then restores active tasks
  at their original absolute root. It preserves the archived original, immutable
  Needs review revision, and valid-lease newer task/project. Lease timing in this
  probe is controlled; the separate H1 probe checks the real 30-second interval.
- [HTTP/Neo4j probe](../../backend/scripts/check_ecc_services.py) uses real HTTP,
  SQLite and a new Neo4j database, with a scripted drafting model and disabled
  semantic embeddings. It checks original-source isolation, immutable revision
  acceptance/reopen/retry, original hashes and stale-owner graph publication.
- [Neo4j cold restore](../../backend/scripts/check_ecc_neo4j_backup.py) stops a new
  synthetic source database, dumps it, loads a new volume, starts the restored
  database and compares all fixture properties. It requires a cached immutable
  image ID and records removal of its own containers and volumes.

## Preparation and superseded evidence

The initial clean rehearsal at `a5368e850d76e0de3090b48ccd2f13a40f9caaa5`
passed 391 backend / 12 Node / 16 component tests, build/audits/Compose, and H1
recovery in 30.01 seconds. Runtime fingerprint was
`d5200973b9aae2eedeb4c3593c7bbf6d6cdbc93d7bc1f6d27085b3a3a3d71fab`.
Its raw evidence remains at `/tmp/crowdlens-ecc-release-rehearsal/` and
`/tmp/crowdlens-ecc-release-prep/`.

An initial 512 MiB Neo4j data tmpfs setup failed transaction-log preallocation;
`/tmp/crowdlens-ecc-release-prep/logs/neo4j-small-tmpfs.log` preserves that setup
failure. A new 2 GiB tmpfs passed after an actual data query, not only a socket
handshake. It was not an application defect or a passed check.

Earlier candidate `3d8ba0e4dbae05a327e1a6cd6684924c31ad1c85` passed the clean
runner, evaluations and cold restores, and built image
`sha256:0f44844dff0e7bdb6fdddd9dce5f2ce3d4f1424a633dc1100769ff509e09dd6c`.
It was superseded for the history-modal contrast correction before C ran image
startup or browser suites. Its [runner receipt](evidence/2026-10-02-release-verification/superseded-3d8ba0e4/receipt.json)
and [image receipt](evidence/2026-10-02-release-verification/superseded-3d8ba0e4/image-prior-receipt.json)
remain distinct from the final candidate.

## Scoped recommendation and actionable backlog

Recommend the tested candidate for bounded local synthetic review. Its clean
installation, tests, browser behavior, component restores and isolated image
startup pass. Real-model end-to-end readiness, independent human quality, exact
remote CI and existing deployment readiness remain blocked, pending or not run.
These findings must not be used to mark every milestone complete.

| Priority | Owner / next action | Evidence boundary |
| --- | --- | --- |
| P1 | Operator/coordinator: choose and separately authorize a suitable local generation model, then run the bounded complete synthetic workflow. | Read-only Ollama inventory contains only `nomic-embed-text:latest` (137M embedding model). Defaults are provider `ollama`, URL `http://localhost:11434/v1`, model `qwen2.5:32b`; that model and H1's `qwen2.5:3b` are absent. Before real workflow testing, approve an exact installed generation model ID, reachable isolated endpoint and bounded resources; keep `EMBEDDING_AUTO_PULL=False`. No model downloads or real inference occurred. |
| P1 | Human reviewers: complete supplied blinded forms and import/scoring procedure on approved held-out material. | Zero completed human reviews; model support/omission/accuracy and review effort remain unmeasured. |
| P1 | Coordinator: after authorization, push and create/update a PR at the candidate, then capture CI for the actual checked-out SHA/tree. | CI triggers on main push or PR, not an ordinary branch push. Default PR checkout may be a merge ref: distinguish it from the head SHA. Do not substitute a later reporting head or another run. |
| P1 | Operator: separately authorize deployment reconciliation with preserved data/configuration. | Existing deployment remains unchanged; current image uses development servers. |
| P2 | Product/backend owner: define aggregate root-generation calls, elapsed-time and cost policy before implementing an aggregate budget. | The measured retry probe characterizes transport behavior; there is no existing total-root budget. |
| P2 | Operations/backend owner: define coordinated backup, retention and supported storage-root migration. | Cold component restores pass; active resources retain absolute roots. No active relocation, hot cross-store snapshot or power-loss claim. |
| P2 | Backend owner: specify runner ownership and memory-loss guarantees, then test remaining restart/storage failure cases. | PID reconciliation and best-effort memory files do not promise exact-round continuation or lossless cognition/history. |
| P3 | CI maintainer: pass the checked-out revision into the Docker build argument. | Current CI Docker job does not supply `CROWDLENS_BUILD_REVISION`; this local image build explicitly does. |
| P3 | Maintainer: select lint/type/coverage targets and Python/container vulnerability scanning. | No configured commands or coverage percentage. Python and container CVE scans were NOT RUN; Python compatibility checks do not measure vulnerabilities. |
