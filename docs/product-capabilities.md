# CrowdLens product capabilities

Evidence date: 2026-10-03. Original Milestone 1 baseline: `main` at `34275b7`.
Method: ECC `product-capability`, followed by the installed ECC 2.2.3 audit,
evaluation, browser and verification workflows. Current local source/evidence
identities are in the [control/recovery audit](audits/2026-10-03-control-recovery.md)
for `34ad6d2`; the prior [execution handoff](audits/2026-10-02-ecc-milestones-3-5.md)
retains the separate `242b899` evidence and completion statuses.
Milestone 1 was documentation-only; subsequent scoped implementation remains local.
Existing deployment equivalence has not been established.

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
- Root generation retries reuse one logical `request_key` and return the existing
  task/report while the task record is retained. Changed parameters conflict;
  a new manual attempt uses a new key. It remains within the separately authorized
  workflow's durable physical-request and wall-time allowance; a new task/key
  cannot reset consumption. Monetary admission remains open.
- Generation requires explicit provider/model/endpoint and frozen-input
  authorization. All stages, applicable children and actual transport retries
  share atomic request admission. Stop prevents new calls and follow-on work,
  preserves partial outputs and records measured/unknown in-flight usage.
  Local cancellation cannot guarantee cancelled provider billing. Recovery is
  explicit and needs new authorization; polling/refresh never provides it.
- Owned background attempts must retain their worker token, lease and resource
  binding before publication or destructive ensemble operations. Recovery preserves
  newer active owners and requires explicit manual retry of abandoned work.
- Existing persisted identifiers and storage compatibility remain intact.
  Original authorship and AGPL licensing remain in place.
- The supported verification baseline is Python 3.11 and Node 22. The declared
  Python range is broader than the verified dependency-lock compatibility.

### Architecture preferences and trust boundaries

- Default deployment is one operator on loopback, with restricted local CORS.
  Authentication, tenancy, and public hosting are future scope.
- Neo4j owns graph entities, edges, original chunks, embeddings, and optional
  agent memories. SQLite owns project/case/task metadata and runner state.
  SQLite also owns workflow authorizations and physical-attempt receipts. The
  filesystem owns documents, scenario files, logs, reports, and proposals.
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
  A completed preparation may be reused unless regeneration is requested. Active
  or failed preparation ownership takes precedence over old files; polling never
  promotes a preparing state to ready. [API regressions](../backend/tests/test_prepare_recovery_api.py)
  verify honest failure and manual retry.
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

Whole-workflow admission now adds a durable provider/input/request/deadline
contract across these operations. It supports primary generation and configured
local Ollama embeddings; secondary generation, remote embeddings and enabled
Jev paths are excluded from this allowance. Structured interruption is terminal
for polling. Effective validated settings reach preparation and execution;
specialized legal aliases are disabled in the UI while retaining shared legacy
backend compatibility. See [the execution controls](workflow-execution.md).

## Verification evidence and priority gaps

### Current local execution evidence

- [Control/recovery verification](audits/2026-10-03-control-recovery.md) at
  `34ad6d2`: 545 passing tests/build, 504 repeated structural cases, H1 recovery,
  synthetic cold restore, 12 workflow and 10 separate browser checks at three
  widths, visible Stop/refresh and actual immutable acceptance/reopen, dependency
  audits and independent review scope. Generation is substituted/blocked. New
  clean-install/image/CI and real Neo4j/OASIS/provider checks are not claimed.
- [Historical request accounting](audits/2026-10-03-bike-lane-request-accounting.md)
  reconstructs 30 MiniMax-M3 requests on `242b899`. That live run reached actual
  simulation but stopped before report completion/proposal review. It does not
  verify the repaired candidate. The [fresh visible-browser plan](visible-browser-acceptance.md)
  freezes the fictional packet and awaits new bounded authorization.
- Versioned synthetic development/holdout fixtures, deterministic source/revision/
  lifecycle checks, three-repeat measurements, and blinded blank human forms are
  available in [the evaluation guide](evaluations/evidence-quality.md). The frozen
  before/after baseline preserves two reproduced root-duplication failures and
  their unchanged passing assertions after repair. Real-model metrics remain
  unmeasured; absent human labels are pending, never zero-error results.
- [Built-UI QA](audits/2026-10-02-milestone4-browser-qa.md) covers responsive, keyboard,
  source/proposal/revision and recovery states with explicit seeded/substituted
  generation stages. It establishes a first visual baseline, not a historical
  regression comparison or a full model-backed workflow.
- [Release evidence](audits/2026-10-02-milestone5-release-verification.md) records
  exact-candidate clean installs, applicable checks, dependency audits, real
  storage probes, cold restore and isolated image identity/readiness. Its status
  does not transfer to another commit or the existing deployment.
- [H1 integration review](audits/2026-10-02-h1-integration-review.md) records two
  additional reproduced readiness/ensemble races, scoped repairs, and retained
  fail-first tests. Worker ownership evidence remains separate from OASIS
  exact-round continuation and memory completeness.

### Historical Milestone 1 evidence

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
| P1 | Historical browser identity is known, but the repair candidate is not deployed. | Historical `242b899` and new `34ad6d2` are distinct. Under a separately authorized deployment task, reconcile the chosen revision and rerun status, report/revision routes and frontend checks; preserve data/configuration. |
| P1 | No fresh upload-to-reviewed-revision run across all real services. | One bounded synthetic document through upload, Neo4j graph build, scenario preparation, simulation, root report, proposal and revision; record IDs, source scope, timings and failure/retry outcomes. Choose local or explicitly authorized hosted inference first. |
| P1 | Report/evidence quality is not independently established. | Approved held-out source packets, independent claim/omission labels, measured reviewer time, and baseline/proposed evaluation. Committed synthetic unreviewed fixtures prove metric mechanics only. |
| P2 | Memory continuity and recovery across processes remain partial. | Exercise actual subprocess restart/forced restart, corrupted or failed memory writes, source separation and graph write failure; demonstrate retained/lost data explicitly. |
| P2 | Full browser flow still requires actual generation/OASIS prerequisites. | Repeat the bounded built-UI checks with real extraction, scenario generation, simulation and root report; current seeded-stage QA and automated accessibility checks cannot certify the complete live pipeline. |
| P2 | Deletion/retention and coordinated multi-store recovery are incomplete product contracts. | Cold SQLite/artifact and separate Neo4j restores are rehearsed. Define retention/deletion ownership, coordinated backup points, and any relocation contract before promising online atomic restore or active-task path changes. |
| P2 | Monetary ceiling and real-provider aggregate control verification remain open. | Physical-request/time limits now have synthetic concurrency/restart/Stop tests and a written contract. Collect fresh actual-provider receipts; define separate monetary admission before claiming a dollar ceiling. Historical transport characterization is not a live duration/cost measurement. |
| P2 | Exact-candidate remote CI is pending. | Obtain authorization to push the reviewed local branch and open/update its PR, then collect checks with the actual checkout SHA/tree; feature-branch push alone does not trigger this workflow, and an older main run is not candidate evidence. |
| P3 | Hardware, latency, coverage and supported Python ranges need measurements. | Repeatable workload/model/hardware benchmarks; documented coverage gaps; clean installs and checks before claiming additional Python versions. |

## Non-goals and remaining decisions

The current work does not deploy the application, enable a provider, execute paid
inference, download a generation model, activate advisory policies, introduce
multi-user hosting, certify predictions, or automatically publish model output.
Milestone 1 changed only documentation; later milestones contain bounded repairs
and synthetic verification described in the dated reports.

Next owners must establish a suitable local generation model or explicitly
permitted hosted provider/input/budget, obtain independent human labels for the
blinded packets, authorize exact-candidate remote CI, and separately plan deployment
reconciliation. Retention/deletion and monetary admission need explicit
contracts. Request/time admission is implemented and synthetically verified.
These decisions do not invalidate completed independent checks, and
those checks do not satisfy the missing decisions.

## Handoff

The capability inventory is maintained alongside the [ECC workflow](ECC-WORKFLOW-PLAN.md)
and [consolidated execution report](audits/2026-10-02-ecc-milestones-3-5.md).
Use their exact source identities and separate status table when selecting the
next bounded task. New features must define their states, interfaces and acceptance
evidence; generated report quality still requires independent assessment.

## Historical Milestone 2 audit — 2026-10-02

The [dated audit](audits/2026-10-02-milestone-2-agent-audit.md) records isolated
source fixes for generated-origin evidence, graph selection, chat roles/context
and interview argument bounds. Regression tests pass. Real disposable Neo4j,
SQLite and HTTP proposal acceptance preserve the parent and unselected section,
produce one child on retry and retain Needs review. Drafting uses a deterministic
model substitute; factual quality remains unverified.

**Historical H1 finding, superseded by the follow-ups below:** a two-process
probe originally restored an abandoned graph-build task as processing. Owned
task recovery and the later readiness/ensemble call-site repairs address that
source defect. Simulation runner reconciliation still does not establish exact
continuation.

Runtime identity is unverified against the desired source: the running image
contains older source, and the new fingerprint instrumentation is not deployed.
Provider-backed upload/ontology failed because the local generation model was
unavailable; graph → scenario → simulation → report remains unverified as a full
current-source workflow. Broader browser and independent quality evaluations
were later milestones at that audit snapshot. Current evidence is linked above;
these historical limits are not silently relabeled as passes.

## Initial H1 follow-up — 2026-10-02

The [H1 remediation addendum](audits/2026-10-02-h1-task-recovery.md) supersedes
the earlier unresolved H1 status for the isolated source. New generic tasks have
persisted worker/attempt ownership, periodic recovery and publication fences.
Real two-process, API/manual-retry and related-state regressions pass; legacy
ownerless tasks remain explicitly uncertain. The fresh full check passed 419
tests and the production frontend build. Existing deployment reconciliation,
full provider workflow and measured report quality remain open. This follow-up
does not declare later milestones or release readiness complete.

The [integration-review addendum](audits/2026-10-02-h1-integration-review.md)
records the subsequent preparation-readiness and stale-ensemble fixes. Final
combined checks and any remaining gaps are in the current execution handoff.
