# CrowdLens product capabilities

Evidence date: 2026-10-02. Source baseline: `main` at `34275b7`.
Method: ECC `product-capability`, using its capability-contract template.
Milestone 1 changes documentation only; the isolated Milestone 2 follow-up is
recorded below and does not describe a deployed change.

## Capability

A local operator can ingest documents or website text, build a source-linked
knowledge graph, configure a scenario, run simulated agents, generate a report,
and review a source-grounded proposal before saving a separate report revision.
This manifest describes what exists, the conditions under which it works, and
what still needs verification. It does not certify predictive accuracy.

Status vocabulary: **implemented** means routes and service behavior exist;
**partial** means only part of the promise is supported; **planned** means future
scope; **unverified** means the required operational evidence was not collected.
Implementation status and live verification are separate dimensions.

## Constraints

### Fixed rules and invariants

- Simulation events and model judgments are generated artifacts. Source
  attribution and structural checks do not certify factual truth or forecasts.
- Proposal retrieval must retain the report's graph, case, and case-version
  scope. Missing/inconsistent scope or missing original source chunks prevents
  useful drafting; arbitrary report text is not substitute evidence.
- Acceptance saves a distinct immutable revision, preserves the parent and
  unselected sections, and leaves the revision `needs_review`. It does not run
  another simulation or issue a fresh prediction.
- Proposal creation retries reuse `request_key`; acceptance retries reuse the
  displayed `proposal_digest`. Reads never schedule drafting.
- Existing persisted identifiers and storage compatibility remain intact.
  Original authorship and AGPL licensing remain in place.
- The supported verification baseline is Python 3.11 and Node 22. The declared
  Python range is broader than the verified dependency-lock compatibility.

### Architecture preferences and trust boundaries

- Default deployment is one operator on loopback, with restricted local CORS.
  Authentication, tenancy, and public hosting are future scope.
- Neo4j owns graph entities, edges, original chunks, embeddings, and optional
  agent memories. SQLite owns project/case/task metadata and runner state.
  The filesystem owns documents, scenario files, logs, reports, and proposals.
- Ollama generation and embeddings can remain local. Hosted generation or
  embeddings send inputs to the selected provider. Website ingestion and
  enabled market lookups also use the network.
- Configured SQLite initialization/import failure stops startup. Disabling the
  database configuration explicitly is different from failing to initialize it.

## Implementation contract

### Actors and surfaces

The operator supplies inputs and settings, starts work, reviews evidence, and
manages local backups. Background workers build graphs, prepare scenarios,
run simulations, generate reports, and draft proposals. Models propose output;
they do not approve publication or establish source truth.

UI routes are defined in [routes.js](../frontend/src/router/routes.js): `/`,
`/cases`, `/case/:caseId`, `/case/:caseId/compare`, `/process/:projectId`,
`/simulation/:simulationId`, `/simulation/:simulationId/start`,
`/report/:reportId`, and `/interaction/:reportId`.

### Workflow map

| Stage / status | Inputs and observable outcome | API contract | Storage and evidence |
| --- | --- | --- | --- |
| Upload — implemented | PDF/MD/TXT files and/or URLs plus `simulation_requirement`; creates a project, source documents, case/version metadata, and generated ontology. | `POST /api/graph/ontology/generate`; existing cases can receive documents through `POST /api/graph/case/<case_id>/documents`. | Original/extracted files on disk; project/case metadata in SQLite when configured. [Graph routes](../backend/app/api/graph.py), [case tests](../backend/tests/test_case_litigation_workflow.py), [URL tests](../backend/tests/test_url_fetcher.py). Fresh provider-backed ingestion unverified. |
| Graph — implemented | Project/ontology and chunk/build settings; returns a task ID, builds entities/edges/source chunks, exposes graph data and embedding readiness. | `POST /api/graph/build`; `GET /api/graph/task/<task_id>`; `GET /api/graph/data/<graph_id>`; `GET /api/graph/<graph_id>/embedding-status`. | Neo4j graph/source/vector records; SQLite project/task state; extraction caches on disk. [Build tests](../backend/tests/test_graph_build_speed.py), [embedding tests](../backend/tests/test_graph_embedding_status.py), [provenance tests](../backend/tests/test_source_tracing.py). Fresh full graph build unverified. |
| Scenario — implemented | Project/graph, entity filters, prediction/scenario settings; creates simulation ID, prepares personas and configuration, returns readiness/progress. | `POST /api/simulation/create`; `POST /api/simulation/prepare`; **POST** `/api/simulation/prepare/status`; `GET /api/simulation/<simulation_id>/config` and `/profiles`. | Simulation `state.json`, profiles, and configuration on disk. This preparation state is distinct from SQLite runner state. [Manager](../backend/app/services/simulation_manager.py), [preparation tests](../backend/tests/test_simulation_manager.py). No guarantee of a particular agent count or persona quality. |
| Simulation — implemented; restart fidelity partial | Prepared simulation, platform, rounds, seed, optional graph-memory/economy settings; launches workers and exposes actions/progress. | `POST /api/simulation/start`, `/stop`, `/run-ensemble`; `GET /api/simulation/<simulation_id>/run-status`, `/run-status/detail`, `/actions`, `/timeline`. | SQLite runner metadata plus JSON compatibility mirror; platform databases/logs and memory files on disk; optional memories in Neo4j. [Runner](../backend/app/services/simulation_runner.py), [persistence tests](../backend/tests/test_simulation_runner_persistence.py), [runtime-memory tests](../backend/tests/test_forecast_upgrade.py). Restart reconciliation is implemented; automatic exact-round continuation is not established. |
| Report — implemented; factual quality unverified | Simulation ID, report mode/depth, project graph and requirements; generates outline/sections, progress, evidence and forecast artifacts. | `POST /api/report/generate`, `/generate/status`; `GET /api/report/<report_id>`, `/<report_id>/progress`, `/<report_id>/download`; root reports support explicit resume/section regeneration. | Report JSON/Markdown, sections, logs and progress on disk; generation tasks in SQLite. [Report routes](../backend/app/api/report.py), [quality tests](../backend/tests/test_report_quality_gates.py), [grounding tests](../backend/tests/test_report_source_grounding.py). Unsafe embedding readiness blocks default generation; `allow_degraded` is an explicit override. |
| Proposal review — implemented; independently measured quality unverified | A saved completed/needs-review report with original source scope; drafts a selected section plus related summary spans; operator accepts or rejects. | `POST /api/report/<report_id>/evidence-proposals`; `GET /api/report/<report_id>/evidence-proposals/<proposal_id>`; `POST` on `/accept` with digest or `/reject` with `{}`; `GET /api/report/<report_id>/revisions`. | Private proposal/source snapshots, leases, staged revision files, tombstones and separate report revision. [Proposal API](../backend/app/api/evidence_proposals.py), [revision service](../backend/app/services/report_revisions.py), [API tests](../backend/tests/test_evidence_proposals_api.py), [revision tests](../backend/tests/test_report_revisions.py). Fresh synthetic HTTP lifecycle passed; real-source quality remains unverified. |

### States and transitions

- Project: `created → ontology_generated → graph_building → graph_completed`;
  failures use `failed`. Force rebuilding explicitly resets graph-build metadata.
  See [ProjectStatus](../backend/app/models/project.py).
- Scenario preparation: `created → preparing → ready`; failures use `failed`.
  A completed preparation may be reused unless regeneration is requested.
- Runner: `idle → starting → running → completed`, or
  `running → stopping → stopped`, with `failed` on failure. `paused` exists in
  the enums, but that alone does not establish a user-facing pause/resume API.
  Startup marks missing recorded processes stopped/interrupted instead of
  silently claiming they are still running.
- Report: `pending → planning → generating → completed/needs_review`, with
  `failed`, `interrupted`, and stale-progress handling. Completion is a workflow
  state, not factual certification. Root regeneration/resume and immutable
  revision behavior are distinct contracts.
- Proposal: `queued → running → ready/blocked/failed`; a ready proposal can enter
  `accepting → accepted`. Changed parent/source content can make it `stale`;
  rejection is explicit. Abandoned queued/running work becomes failed with an
  interruption reason at reconciliation. Interrupted acceptance can be recovered
  with the original digest. These are summaries of the authoritative
  [transition table](../backend/app/services/proposal_store.py), not new states.

### Failure, retry, and data ownership

Back up SQLite, uploaded files, simulation artifacts, report roots including
hidden proposal directories, and Neo4j together using their documented safe
procedures. There is no single cross-store transaction or established universal
cascade-delete/retention contract. A case version is not a whole-graph snapshot.

Missing source availability is different from changed sources: a temporary outage
keeps acceptance retryable, while changed content invalidates an unpublished
proposal. If a revision was already published before an interruption, retry
recovers that same revision. Deleted revisions are tombstoned and not recreated.
See [report review/recovery](evidence-first-reports.md) and
[control-plane migration](control-plane-migration.md).

Agent memory is **partial**, not entirely in-memory: short-memory and summary
files have load/save helpers in [forecast_runtime.py](../backend/scripts/forecast_runtime.py),
and optional graph updates write memories plus activity text through
[graph_memory_updater.py](../backend/app/services/graph_memory_updater.py).
Bounded buffers, optional enablement, best-effort file writes, and forced-run
cleanup prevent promising complete history or lossless restart continuity.

### Observability and policy

`GET /health` establishes HTTP liveness. `GET /api/status` reports Neo4j,
embedding/vector readiness, control database/import/reconciliation state, model
configuration, and decision-policy configuration. HTTP 200 is not proof that
dependencies are healthy. `llm.configured` is not an inference probe; disk usage
is not currently reported. Workflow progress and request IDs aid diagnosis.

Proposal drafting has bounded source admission, retrieval, model calls, deadline,
and worker capacity. Hosted work already submitted may complete after local
cancellation; observed usage is retained without reviving the proposal. Semantic
proposal retrieval uses local Ollama only and skips remote embedding requests.
See [proposal limits](evidence-first-reports.md) and
[Jev boundaries](jev-evaluation.md). Report chat and agent interviews are optional
follow-up surfaces; interviews depend on a live simulation environment rather
than guaranteeing permanent availability for every saved report.

## Verification evidence and priority gaps

### Fresh evidence in this milestone

- `UV_PYTHON=3.11 npm run check`: 347 backend tests, 12 frontend unit tests,
  16 component tests, and Vite production build passed. Most backend tests use
  isolated files/fakes; they do not establish a full live-provider pipeline.
- Read-only HTTP on port 5001: health/status respond; reported Neo4j, local
  embeddings, vectors, and SQLite are healthy. Generation is configured for a
  hosted provider. Its service label differs from the current source, and the
  revision lookup returned an HTML route-level 404 rather than the current JSON
  error envelope. This strongly indicates deployment drift; the deployed commit
  was not established. No live generation or deployment change was performed.
- The current source's synthetic harness served the built frontend/report APIs
  on a separate loopback port with real providers blocked. HTTP creation/polling
  reached `ready`; acceptance returned a distinct `needs_review` revision;
  repeating acceptance returned the same revision; an unrelated section was
  `blocked`; parent artifact hashes remained unchanged. Evidence is in the
  disposable run directory `/tmp/crowdlens-capability-20261002/`.
- The synthetic check exercised APIs, not visual browser interaction. Full
  browser, accessibility, and responsive checks were not rerun in this milestone.
  Current CI, dependency audits, and image build were not rerun either.

| Priority | Verification gap | Required evidence before strengthening the promise |
| --- | --- | --- |
| P1 | Running deployment does not match current source behavior. | Record deployed revision/build identity; under a deployment task, reconcile it with the intended commit and rerun status, report/revision route, and frontend smoke checks. Preserve data and configuration. |
| P1 | No fresh upload-to-reviewed-revision run across all real services. | One bounded synthetic document through upload, Neo4j graph build, scenario preparation, simulation, root report, proposal and revision; record IDs, source scope, timings and failure/retry outcomes. Choose local or explicitly authorized hosted inference first. |
| P1 | Report/evidence quality is not independently established. | Approved held-out source packets, independent claim/omission labels, measured reviewer time, and baseline/proposed evaluation. Committed synthetic unreviewed fixtures prove metric mechanics only. |
| P2 | Memory continuity and recovery across processes remain partial. | Exercise actual subprocess restart/forced restart, corrupted or failed memory writes, source separation and graph write failure; demonstrate retained/lost data explicitly. |
| P2 | Proposal review browser usability and accessibility need current evidence. | Real built UI at desktop/mobile widths; keyboard flow, focus/error states, reload after interrupted save, stale proposal and blocked retrieval. |
| P2 | Deletion/retention and multi-store restoration are incomplete product contracts. | Define ownership and retention decisions, then rehearse a consistent restore and scoped deletion with synthetic data across SQLite, artifacts and Neo4j. |
| P3 | Hardware, latency, coverage and supported Python ranges need measurements. | Repeatable workload/model/hardware benchmarks; documented coverage gaps; clean installs and checks before claiming additional Python versions. |

## Non-goals

This milestone does not change application logic, deploy/rebuild containers,
enable new providers, run paid inference, introduce authentication/multi-user
hosting, certify predictions, or establish automatic publication of model output.
It does not replace [architecture](architecture.md), detailed recovery docs, or
the [ECC workflow plan](ECC-WORKFLOW-PLAN.md).

## Open questions

No unresolved product decision blocks this documentation milestone. Before new
implementation, settle the relevant decision: which source revision should run
locally; whether the full-pipeline check uses local or hosted inference and its
budget; who independently labels report quality; what retention/deletion promises
are intended; and whether public/multi-user deployment is actually desired.

## Handoff

The capability inventory and documentation reconciliation are complete. The next
bounded lane is `ecc:agent-architecture-audit` for the P1/P2 agent, source-scope,
retry and recovery boundaries, followed by targeted `ecc:verification-loop`
checks. Deployment reconciliation needs its own operational task; evaluation
quality needs independent labels before making improvement claims. New features
should use this manifest to define their states, interfaces and acceptance evidence.

## Milestone 2 evidence — 2026-10-02

The [dated audit](audits/2026-10-02-milestone-2-agent-audit.md) records isolated
source fixes for generated-origin evidence, graph selection, chat roles/context
and interview argument bounds. Regression tests pass. Real disposable Neo4j,
SQLite and HTTP proposal acceptance preserve the parent and unselected section,
produce one child on retry and retain Needs review. Drafting uses a deterministic
model substitute; factual quality remains unverified.

**Highest priority: generic task restart recovery is incomplete.** A two-process
probe restores an abandoned graph-build task as processing. Worker ownership and
coordinated project/task recovery require remediation. Existing runner
reconciliation does not establish generic task recovery or exact continuation.

Runtime identity is unverified against the desired source: the running image
contains older source, and the new fingerprint instrumentation is not deployed.
Provider-backed upload/ontology failed because the local generation model was
unavailable; graph → scenario → simulation → report remains unverified as a full
current-source workflow. Broader browser and independent quality evaluations
remain later milestones. These limits do not strengthen implementation promises.

## H1 follow-up — 2026-10-02

The [H1 remediation addendum](audits/2026-10-02-h1-task-recovery.md) supersedes
the earlier unresolved H1 status for the isolated source. New generic tasks have
persisted worker/attempt ownership, periodic recovery and publication fences.
Real two-process, API/manual-retry and related-state regressions pass; legacy
ownerless tasks remain explicitly uncertain. The fresh full check passed 419
tests and the production frontend build. Existing deployment reconciliation,
full provider workflow and measured report quality remain open. This follow-up
does not declare later milestones or release readiness complete.
