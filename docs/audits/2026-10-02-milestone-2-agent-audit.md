# CrowdLens Milestone 2 agent architecture audit

Date: 2026-10-02. Skill: installed ECC 2.2.3 `agent-architecture-audit`.

**Audit finished; Milestone 2 remediation incomplete.** One confirmed high
reliability failure remains: generic tasks retain `processing` after their writer
exits. Five confirmed high boundary failures were corrected in isolated source.
The current deployment differs from the intended source and was inspected only.
The full workflow is **blocked**, not passed. This is not release approval.

## Baseline and authority

Intended baseline: `main`, `34275b75223dee82087ff6ac937c4fc6e4af9323`.
Original checkout contained modified README, ROADMAP, architecture documentation
and untracked ECC plan/capability manifest. Those Milestone 1 changes were saved
before isolation and preserved. No original application files were changed.
Audit code is on local branch `codex/crowdlens-milestone2` in a managed worktree;
Milestone 1 documentation overlays are excluded from its audit commit.
Only the worktree plan and manifest receive a separately identifiable evidence update.
All five original Milestone 1 files remain byte-for-byte unchanged; the copied
plan/manifest updates remain unstaged alongside their Milestone 1 overlays.

The supplied AGENTS instructions require graph-first discovery. Graph searches
found the older LLM wrapper but did not find current proposal/revision services;
reported line ranges also disagreed with source. Source files were therefore the
authority. No index refresh or claim of complete graph coverage was made.
Read the plan, capability manifest, architecture, evidence-first report and
control-plane recovery documentation before assessing changes.

Tested source fingerprint: `0dffb21395e1be16188d721f3d29cd8f19e2a9d0f9e5b1e7c0e348e187073176`
(`runtime-source-v1`). This identifies the audit source overlay, not clean main.
The fingerprint covers selected runtime files/manifests, not tests, docs, operator
configuration, installed binaries or private data. It is not signed provenance.

## Severity-ranked findings

### H1 — orphaned generic tasks remain processing: confirmed, unresolved

Layer 12, persistence; confidence 1.0. A synthetic writer creates a graph-build
task in disposable SQLite, marks it processing and exits. Another process reads
`processing`; no owner identity or lease distinguishes dead from live writers.
[Task creation/restoration](../../backend/app/models/task.py#L99) persists status;
[startup wiring](../../backend/app/services/control_plane.py#L42) reconciles
simulation runners, not generic tasks. [Graph build](../../backend/app/api/graph.py#L618)
rejects repeated builds while the project remains building. The probe directly
confirms orphaned task status; the project polling consequence is source evidence.

Reproduction: `backend/.venv/bin/python backend/scripts/probe_milestone2_task_restart.py`
returns **1**, with `writer_process_exited=true`, `restored_status=processing`.
Recorded task: `4a49203f-26df-4385-a140-6b51a36a6ff5`. It uses two processes and a
new temporary database; no inference or existing services/data.

Required next fix: persist worker identity and ownership/lease state, then
reconcile abandoned task and associated project/report state to an honest failed
or interrupted result. Test dead owners, live other backend workers, PID reuse,
legacy ownerless tasks, and interruption around each write. Do not imply automatic
continuation. A blanket startup failure sweep could invalidate another backend's
live work; that change was not made without the necessary ownership contract.

### H2 — generated episodes promoted to original evidence: confirmed, fixed

Layers 3/4/8/12; confidence 1.0. Correctly scoped rows carrying a document ID but
an explicit simulation, memory, or report origin were admitted and relabelled as
`source_document`. Procedural covers could likewise anchor source roles from
memory. Hybrid search also overwrote an explicit generated origin.

Code gates now reject explicit non-document origins in
[SourceIndex](../../backend/app/services/source_tracing.py#L23) and
[procedural grounding](../../backend/app/services/procedural_grounding.py#L11);
[hybrid results](../../backend/app/storage/neo4j_storage.py#L1413) preserve origin.
Legacy missing-origin rows still need a document ID and appropriate scope.
This does not defend against a privileged database writer forging documentary
metadata, or prove semantic factual support.

Fail-first regressions cover three origins, generated covers and hybrid retrieval.
Real disposable Neo4j retrieval excludes wrong-version and generated rows before
proposal drafting. Existing conflict/absent-evidence/source-change tests pass.

### H3 — foreign project graph selectable: confirmed, fixed

Layers 6/8/12; confidence 1.0. Simulation creation accepted a graph override while
attaching the selected project's settings. Existing mismatched simulation state
could then feed report generation or chat.

[Creation](../../backend/app/api/simulation.py#L213),
[new generation](../../backend/app/api/report.py#L140), and
[chat](../../backend/app/api/report.py#L377) now return HTTP 409
`graph_scope_mismatch` before the affected execution. Three failing API fixtures
now pass. This deliberately also blocks old simulation contexts after a project
graph changes; rebuild/reselect a valid context. Previously saved artifacts are
preserved; returning a cached saved root is not certification of its old scope.

### H4 — caller-controlled chat roles enter model instructions: confirmed, fixed

Layers 1/2; confidence 1.0. API history forwarded caller-provided system/tool
roles and malformed content directly into model messages.
[Validation](../../backend/app/api/report.py#L355) now requires at most 100 entries,
exact role/content keys, user or assistant roles and string content up to 15,000
characters. Invalid history returns HTTP 400 before execution. Four fail-first
fixtures pass. The current UI sends exactly role/content pairs. History text
still requires untrusted-content treatment; this is an API role boundary.

### H5 — saved generated report inserted into system prompt: confirmed, fixed

Layers 1/2/4; confidence 1.0. Saved report text was formatted into the chat system
message, promoting generated content to instruction priority.
[Chat assembly](../../backend/app/services/report_agent.py#L2695) now supplies it
as a separately labelled user context message, explicitly generated and untrusted.
The fail-first message-capture test proves report text is absent from system
messages. This role separation is deterministic; resistance to instructions in
arbitrary document/history text remains a model-dependent, unverified property.

### H6 — negative interview count bypasses cap: confirmed, fixed

Layers 6/7/11; confidence 1.0. The model tool used `min(value, 10)` without a
positive bound. A value of -1 sliced a 20-agent selection to 19, exceeding the
intended cap. [Argument gate](../../backend/app/services/report_agent.py#L1423)
rejects nonpositive counts and booleans; positive values remain capped at ten.
Three fail-first regressions verify no interview service execution for -1, 0 or
true. The guarantee applies to the model-facing router, not arbitrary direct
calls to a private selection helper.

### M1 — deployment identity missing and drift: confirmed; instrumentation added, deployment unresolved

Layers 10/12; confidence 1.0 for mismatch, lower for exact historical revision.
Details below. [Identity helper](../../backend/app/utils/build_identity.py#L9),
status and health responses now expose a non-secret source fingerprint plus an
optional 40-hex declared revision. Dockerfile records the supplied revision in
OCI metadata/environment. Two fail-first identity tests now pass, including
source change sensitivity and exclusion of operator data/configuration.
The declared revision is an operator assertion; dirty source can differ from it.
Nothing establishes the existing runtime from instrumentation not deployed there.

### M2 — root retry amplification and duplicate generation: source-confirmed mechanism, untested fault outcome

Layers 6/11/12; confidence 0.9 for retry mechanism, 0.6 for duplicate outcome.
[Frontend](../../frontend/src/api/report.js#L8) retries generation three times;
its generic retry helper retries all errors. New root generation uses fresh
report/task IDs and checks a terminal saved report, without an in-flight request
key. A response loss can plausibly duplicate expensive generation. No such fault
was injected; do not present duplicate artifacts as observed. Add response-loss
and concurrent root-generation tests before choosing an idempotency fix.

### M3 — partial runner/memory recovery: confirmed limits, additional risks untested

Layers 3/4/12. SQLite runner state takes precedence over its JSON mirror.
[Reconciliation](../../backend/app/services/simulation_runner.py#L361) detects
missing recorded PIDs, but does not prove ownership when a PID is reused or
resume exact rounds. PID reuse is an untested hypothesis. Existing dead/live PID
fixtures pass. [Short-memory and summary writes](../../backend/scripts/forecast_runtime.py#L42)
catch filesystem errors; force preparation clears memory. Saved state is durable
where tested, in-flight cognition is not losslessly recoverable.
Extraction cache keys include text/file and ontology hashes, but not model/prompt
identity; fresh provenance is stamped on reused extraction. Model-change quality
staleness is a source-level risk, not an observed cross-case evidence leak.

## Deployment identity diagnosis (read-only)

| Component | Established evidence | Match to intended source |
| --- | --- | --- |
| Existing backend/frontend app image | ID/digest `sha256:75ff5216715c4b6e9b7187bcc1567ec189ac8225d234bb59d8f38b41dfe8ec68`; created 2026-09-21 12:11:13 -04:00; recorded start 2026-10-02 05:55:13Z; Node 20.19.2. OCI revision absent. | Does not match current main. Proposal API file missing; status, report agent, model wrapper and frontend report client hashes differ. |
| Existing graph service | Neo4j 5.18 community, image `sha256:8f01f7bb053e5564eb84a3f1824e4ca2202d29dd415d196cf8e27c8f7e6b611e`. | Service version established; graph contents/backup integrity intentionally not inspected. |
| Existing model service | Image `sha256:a6149234667efc71d37766d61c1a16f24c33e4cd7a0bf4125c44a7e47e2419c4`, running a latest tag; checkout Compose pins 0.32.6. Read-only tags list only `nomic-embed-text:latest`. | Version configuration differs; required generation model unavailable. |

The app's Compose build context is the primary checkout, but its source was
copied into the older image. Only the upload directory is bound into that
container; there is no source bind mount. Writable-layer inspection found no
application-source modifications. Five sampled runtime files matched six older
ancestor revisions; that narrows provenance but cannot identify the exact full
revision. Updating the checkout alone therefore does not update embedded source.
The old display label is corroborating evidence, not the identity proof.

At port 3000 the served development client resolves same-origin `/api`; Vite
proxies to `localhost:5001` inside the app container. Status through 3000 and
5001 agrees. The previously shown 4173 preview was unavailable at inspection.
Whitelisted runtime configuration reports MiniMax-M3 and the local embedding
model. No hosted inference was requested and no credentials were recorded.
Existing dependency ports are bound broadly despite current Compose loopback
bindings. That operational discrepancy remains; no live bindings were changed.
No existing service was restarted, replaced, migrated or cleaned up.

## Trace and all applicable ECC layers

| Layer | Trace and boundary | Assessment |
| --- | --- | --- |
| 1 System prompt | Ontology documents → LLM; ReportAgent templates/tool descriptions; saved report → chat. | H4/H5 fixed at role boundary; semantic document injection not certified. |
| 2 Session history | API → validated user/assistant messages → last ten entries in chat. | H4 fixed; arbitrary history truth remains unverified. |
| 3 Long-term memory | Per-simulation short memory/summaries and optional Neo4j episodes. | H2 origin fixed; memory save limits retained. |
| 4 Distillation | Memory summary updates and saved report reused as context. | Generated summaries are not original evidence; best-effort persistence. |
| 5 Active recall | Report source grounding, search fallbacks, agent memory context. | Applicable retrieval inspected; separate coding-assistant recall service not part of product. |
| 6 Tool selection | Report tool JSON parser/router; optional interview/decision hooks. | Supported routes gated; required-tool wording alone does not enforce a call. |
| 7 Tool execution | Router → graph/interview tools → execution logs/results. | H6 fixed; logs show local dispatch, not independent provider execution attestation. |
| 8 Tool interpretation | SourceIndex/claim ledger and provenance envelopes; empty/error result paths. | Scope/origin checks enforce structure; root prose can still misinterpret output. |
| 9 Answer shaping | Grounding/quality warnings; section assembly; JSON proposal validation. | Claim/status persistence and conflict/absence fixtures pass; factual quality unmeasured. |
| 10 Platform rendering | Report API → report client → EvidenceDraftReview/SafeMarkdown. | Component/Node tests cover escaped content and review constraints; no full browser QA. |
| 11 Hidden repair loops | Provider retries, root section loops, conflict repair, deep-search/interview auxiliary calls. | Proposal budget tested; root aggregate cost/duration not bounded by one request budget. |
| 12 Persistence | SQLite metadata; filesystem reports/proposals/revisions; Neo4j sources/memories. | Revision recovery tests pass; generic task recovery H1 unresolved. |

No separate coding-assistant orchestration, SOP distillation daemon, or external
active-recall service is in scope. Their hypothetical behavior is inapplicable;
product retrieval and memory layers above remain applicable.

Representative trace: upload → case/version/project persistence → ontology model
call → asynchronous graph build/cache → scoped source episodes → scenario state →
OASIS worker/runner metadata → source grounding + tools → saved root report →
proposal request-key/lease → scoped frozen sources + bounded drafting → ready
proposal digest → locked acceptance/parent/source validation → staged publication
→ immutable child → needs-review UI. Graph fallback results without source
provenance remain unverified, not inferred original documents. Evidence proposal
and root-report paths have materially different validation/budget strength.

### Budgets and side effects

| Path | Source contract | Verification limit |
| --- | --- | --- |
| Frontend generation/chat | Three request attempts, retry helper catches all errors. | Response-loss/idempotency fault tests absent. |
| Root provider wrapper | OpenAI SDK default two retries; Anthropic adapter default four retries, timeout default 300 seconds. | Overrides exist; no live hosted fault tests. |
| Root agent | Up to five section iterations plus final pass; chat two iterations; conflict repair and query/interview/summary/claim auxiliary calls can add calls. | No aggregate root wall-clock/spend/call budget proved. Per-loop counts are not a whole-request cap. |
| Evidence proposal | Up to three drafting calls; zero provider retries, per-call timeout ≤60 seconds/remaining time; 180-second watchdog; bounded sources/embedding queries. | Existing timeout/cancellation tests fence late results, retain usage and capacity; remote work cannot be forcibly uncomputed. |
| Jev/decision hooks | Budgeted runner exists; admission/cache/decision configuration separate from report facts. | Advisory modes off in audit; no policy activation or reserved evaluation execution. |
| Proposal acceptance | Digest and request/revision identity; lease and staged durable publication. | Bad digest, concurrent acceptance, retry and interrupted publication pass; no guarantee about arbitrary power-loss/storage faults. |

SQLite is authoritative for configured project/case/task/runner metadata; startup
fails closed on initialization errors. Filesystem owns simulation preparation,
platform artifacts, report sections/Markdown/proposals/revisions. Neo4j owns graph
source chunks, derived entities/edges and optional generated memories. No single
storage transaction covers all three. Unit/API fault tests and the restart probe
support specific boundaries, not a full backup-and-restore certificate.

## Verification evidence and commands actually run

All checks used synthetic fixtures and the isolated source. The original data,
private case documents and reserved evaluations were not consumed.

| Evidence category | Command/check and result |
| --- | --- |
| Source inspection | Graph lookups, direct source traces, read-only container metadata/file hashes, HTTP status and Ollama model inventory. Drift confirmed; full runtime revision unknown. |
| Fail-first regressions | Boundary, hybrid-origin, identity, negative-cap and mismatched-context tests failed on the baseline before each fix, then passed. Twenty new passing test cases overall, including two additional acceptance/recovery tests. Sanitized red summaries retained in temporary evidence. |
| Current repository checks | `UV_PYTHON=3.11 npm run check`: **367 backend + 12 Node + 16 component tests pass**, production Vite build passes. No absent lint/type/coverage checks claimed. |
| Dependency audits | `npm audit --audit-level=moderate` and `npm audit --prefix frontend --audit-level=moderate`: zero vulnerabilities reported at inspection. |
| Fresh installation | `UV_PYTHON=3.11 uv sync --frozen --dev --offline --project backend` passes with independent environment. Offline npm installs fail with ENOTCACHED; fresh `npm ci --ignore-scripts` root and frontend pass using registry access. No secret environment file copied. |
| Compose | Initial env-file attempt fails because service expects `.env`. A disposable rendered Compose file points to `.env.example` and synthetic password; `docker compose -f /tmp/crowdlens-m2-evidence/compose-synthetic.yml config --quiet` passes. Existing configuration unchanged. |
| Image build | `docker build --build-arg CROWDLENS_BUILD_REVISION=34275b75223dee82087ff6ac937c4fc6e4af9323 -t crowdlens-m2-audit:local .` passes. New isolated image ID `sha256:9690e71c6d3db9c25f80b566dfe41a5495557e6a88b82e9abead4e075d0e9782`. Network-disabled helper execution passes using its backend virtual environment. Fingerprint `e155cff9e9f5ecade37cf68fb8eba93975616123d7615575d40ce2caa8ad67a1` differs from final worktree: the image copied an earlier audit snapshot before final diagnostic-script updates. Per-file comparison confirms only the two diagnostic scripts differ; application files match. Its declared base revision does not identify dirty changes. This image was not deployed or certified as the final delivered source. |
| Recovery | Full suite includes dead/live runner PID checks; changed parent/source, interruption before/after revision publication, immutable API/writer guards, proposal timeout/cancellation tests. New concurrent acceptance and fresh-store post-publication retry preserve one child, parent bytes and unselected section. These are synthetic fault injections, not a live OASIS crash or machine power-loss test. |
| Known failure reproduction | `backend/.venv/bin/python backend/scripts/probe_milestone2_task_restart.py`: exit 1 confirms H1 in two processes with new temporary SQLite. |
| Real-service integration | Disposable Neo4j 5.18 with tmpfs data/logs, loopback ports; actual Flask HTTP and SQLite. Deterministic drafting LLM and disabled semantic embedding are explicit substitutions. Passed scoped retrieval and proposal API lifecycle below. |
| Full workflow | Actual synthetic upload/ontology API with loopback Ollama: HTTP 500 from provider model-not-found 404. Final harness enforces one inference HTTP request, six-second transport timeout, loopback-only requests. No model pull, hosted call or provider substitution. Later graph/scenario/simulation/report stages **blocked/unverified**. |
| Independent quality evaluation | Not run. No model rubric score, source-selection accuracy, factual quality or forecast accuracy asserted. Milestone 3 not started. |
| Browser/CI | No comprehensive browser pass or fresh GitHub CI run. Milestone 4 not started; no push or merge. |

Repeat real-service integration against a **new empty disposable** Neo4j with the
script's synthetic credentials, never the existing database:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/smoke_milestone2_boundaries.py \
  --synthetic --neo4j-uri bolt://127.0.0.1:32769 \
  --output-dir /tmp/crowdlens-m2-integration-bounded
```

Only the newly created disposable Neo4j container was removed after verification;
the existing deployment and volumes were untouched.

Recorded HTTP port 39529; parent `report_root`; proposal
`proposal_70c72f45db494de5977a53d7f1e4200a`; child
`report_ef26c3d0d429405da37f87728cd2304c`; upload project
`proj_a9d95c7670d7`. One proposal creation, three acceptance requests
(stale digest → 409, acceptance → child, retry → same child). Parent hashes and
unselected section unchanged; immutable mutation endpoints return 409; child
remains `needs_review`. Earlier iterations repeated this synthetic check while
instrumenting the harness; every upload attempt failed locally for missing model,
and none completed the full workflow. Real service storage is exercised; provider
quality and full OASIS behavior are not. Local temporary logs/results are under
`/tmp/crowdlens-m2-evidence` and `/tmp/crowdlens-m2-integration-bounded`.

## Remaining priorities and stopping boundary

1. Resolve H1 with owned task recovery and regression evidence before declaring
   Milestone 2 remediation complete.
2. Address root request idempotency/aggregate budgets after concrete fault tests.
3. Plan a separately authorized deployment reconciliation and availability of a
   local generation model; repeat full workflow with exact component identity.
4. Test graph fallback/embedding failure, real runner interruption, PID reuse,
   filesystem write failures and disposable backup/restore at relevant boundaries.
5. Measure report quality and broader browser behavior in their later milestones.

The existing deployment remains unchanged. Fixes are local and unmerged. Audit
completion, remediation completion, deployment verification and report-quality
verification are separate verdicts; only the first is complete here.
