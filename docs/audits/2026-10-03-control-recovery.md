# CrowdLens control and recovery repair — 2026-10-03

Settings propagation, Stop, interrupted-report polling, and aggregate request/time
controls are repaired on local branch `codex/crowdlens-control-recovery`.
Synthetic verification passed. No additional paid inference, push, main merge,
deployment, model download, or unrelated service change occurred. A full fresh
model-backed workflow and report/proposal quality remain unverified.

## Identities and preservation

| Boundary | Recovered identity |
| --- | --- |
| Historical browser | `http://127.0.0.1:32786/report/report_8c343d6450c0`; backend `127.0.0.1:32787`, served by the isolated bike-lane app container. |
| Historical application | Commit `242b8999044e33c8c3217df857c06401f3efbba3`, tree `39753400064fe764b98152c2c0204005f874a9c1`. |
| Historical source fingerprint | `runtime-source-v1`: `a807c651b35560c12a91ec6f0b79b2d32df7bad60ebf3322d121c643d9e835fb`. Frozen `/health` and the earlier image verification agree. |
| Historical image | `sha256:9d9c9a37c6e892dacb74ca09fe7b3d55e1d5b3aa62e6f89f08b3b5f25929a253`. Built from `/tmp/crowdlens-ecc-release-final-242b8999/image-source`; release checkout `/home/ali/.codex/worktrees/crowdlens-ecc-release/mirofish-local`. Container code is under `/app`; inspected mounts contain data/logs, not a source overlay. |
| Previous reporting HEAD | `31e21730e9f83c23c11537615a748563bafb3b17` was documentation identity, not the browser's application revision. |
| Newly tested application | `34ad6d27e298f33317e443f0123143fa5e865eab`, tree `8bad4a6db9e2b510743fd596f1d934310379cac9`, in `/home/ali/.codex/worktrees/crowdlens-ecc-integration/mirofish-local`. Tracked source was clean at verification completion. |
| New source fingerprint | `runtime-source-v1`: `fea6ca781b9a175fe9face0055dc195bf7f685551e5af5a5f2b42a5342450006`. Final automated and visible preview receipts agree with this candidate. |

[Candidate identity](evidence/2026-10-03-control-recovery/candidate-identity.json),
[historical mounts](evidence/2026-10-03-control-recovery/historical-container-mounts.json),
and [previous image verification](2026-10-02-milestone5-release-verification.md)
support these distinctions. The new code has not replaced the historical app.
The later documentation commit changes reporting identity only; it does not
inherit image, clean-install, CI, or real-service verification for the new code.
The fingerprint excludes documentation, backend tests, frontend browser tests,
and generated bundles. Exact Git identity covers tests; preview receipts record
the built bundle hashes separately.

The original packet, test result, screenshots, and 24 frozen artifact files
remain unchanged: [34-file preservation receipt](evidence/2026-10-03-control-recovery/historical-preservation.json).
The historical app remains untouched; its active polling log can continue growing
and is not one of those frozen files. The main checkout remains `34275b7` with
its five original documentation overlays byte-preserved against the prior
handoff hashes: [main preservation](evidence/2026-10-03-control-recovery/main-preservation.json).

Historical configuration used MiniMax-M3 through the bounded Anthropic relay,
no transport retries, 120-second transport timeout, graph concurrency one, no
graph-batch retries, local Neo4j/Ollama embeddings, embedding auto-pull disabled,
Jev off and market lookups disabled. The relay admitted 30 requests. Full secret
configuration is deliberately absent from repository evidence; the
[request-accounting report](2026-10-03-bike-lane-request-accounting.md) records
the non-secret receipts and remaining unknowns.

## Reproduction and confirmed causes

Failing assertions were retained before each repair. These are product
regressions unless explicitly classified as a harness/setup failure in the
[evidence index](evidence/2026-10-03-control-recovery/README.md).

| Symptom and cause | Before evidence | Repaired behavior and final coverage |
| --- | --- | --- |
| Settings were saved in preparation state but omitted from the configuration worker call. The worker therefore generated default 72-hour/preset configuration. The UI also displayed preset values and defaulted execution to 40 rounds. | [Worker/timestamp/Stop regressions](evidence/2026-10-03-control-recovery/before-regressions.txt), [prepared values](evidence/2026-10-03-control-recovery/before-prepared-control-values.txt), [preparation and rounds](evidence/2026-10-03-control-recovery/before-prepare-and-case-ui-valid.txt). | Validated settings reach the worker, generated config and execution. Prepared values and explicit platform/rounds/seed/memory overrides are displayed. Refresh does not prepare/start a run. Backend and component regressions pass. |
| Some invalid mode/depth/platform settings were silently accepted. Specialized legal mode labels were aliases of a shared implementation rather than separately supported behavior. | [Invalid-settings regressions](evidence/2026-10-03-control-recovery/before-unsupported-settings.txt). | Invalid supported-field values fail validation. UI offers four implemented report modes and disables specialized legal aliases; old aliases remain compatible with the shared backend behavior. Fast depth is persisted and forwarded through generate/resume/regenerate. |
| There was no usable whole-workflow Stop. Memory shutdown drained billable extraction; the monitor could overwrite Stopped with Completed after a clean process exit despite partial rounds. | [Stop and completion regressions](evidence/2026-10-03-control-recovery/before-regressions.txt), [publication/drain](evidence/2026-10-03-control-recovery/before-publication-drain.txt). | Stop first closes durable admission, cancels only the matching owned epoch and retains partial output. Stop skips billable memory draining. Normal completion draining remains accounted. Late usage is recorded without publishing success after Stop; partial exit cannot become Completed. |
| Ownership expiry repaired the task but left plain/ensemble run mirrors Running; a stale process could overwrite newer run state. Process-local readers could miss same-attempt updates. | [Run-state fences](evidence/2026-10-03-control-recovery/before-run-state-fence.txt), [cache regression](evidence/2026-10-03-control-recovery/before-shared-run-state-cache.txt). | Matching expired attempts repair DB/mirror state to Stopped with a reason. Publication and destructive operations retain owner/resource fences. Readers refresh same-attempt progress/completion. No merely recorded or reused PID is signalled. |
| Interrupted progress subtracted naive and timezone-aware datetimes. Failed task state could be hidden by stale progress; terminal UI kept polling, and explicit Resume did not restart polling. | [Original error response](evidence/2026-10-03-control-recovery/historical-report-progress-error.json), [reproduced historical stack](evidence/2026-10-03-control-recovery/historical-progress-reproduced-traceback.txt), [terminal API](evidence/2026-10-03-control-recovery/before-terminal-progress.txt), [terminal polling](evidence/2026-10-03-control-recovery/before-browser-controls.txt), [Resume polling](evidence/2026-10-03-control-recovery/before-resume-polling-valid.txt). | Timestamp handling accepts both forms. Expected interruption returns structured terminal progress, including failed ownership reason. Polling stops; only explicit Resume schedules a new attempt and restarts it. Queued recovery supersedes an old terminal mirror. Missing reports remain 404 and unexpected I/O errors remain 500. |
| Header logic labelled a stopped simulation Running. | [Header regression](evidence/2026-10-03-control-recovery/before-stopped-page-header.txt). | Stopped and Failed labels agree with effective persisted state after refresh. Related text contrast was repaired and checked at all three widths. |
| Existing per-operation limits did not aggregate root stages, graph-memory calls, children or retries. New control integration also exposed GET/recovery response rebinding and automatic generation retry defects. | [Missing-ledger contract](evidence/2026-10-03-control-recovery/before-allowance.txt), [unscoped admission](evidence/2026-10-03-control-recovery/before-unscoped.txt), [GET binding](evidence/2026-10-03-control-recovery/before-read-only-resource-binding.txt), [recovery binding](evidence/2026-10-03-control-recovery/before-recovery-related-binding-valid.txt), [generation retry](evidence/2026-10-03-control-recovery/before-generation-retry-valid.txt). | Atomic SQLite admission counts every physical transport attempt across the workflow. Polling and manual attempts preserve consumed requests. Reads and recovery responses never rebind existing related artifacts. Only newly created supported artifacts gain a binding. Unsafe automatic generation retries are removed. |

The historical response proves HTTP 500 with
`can't subtract offset-naive and offset-aware datetimes`. The retained original
application log has no full traceback for that handled exception. The linked
stack is an explicitly labelled reproduction invoking the exact historical
method on frozen progress, not a recovered production stack. The original
report had three outline sections, zero completed sections, 12 evidence cards,
an interrupted progress record and a failed generation task. It remains a
partial failed run.

### Settings traced through execution

The historical selections were four profiles, profile parallelism one, two
hours, 60 minutes per round, four active agents, baseline scenario, one ensemble
run, Evidence gap and Fast. Four profiles and parallelism one worked. Duration,
active-agent cap, scenario/ensemble configuration and report mode/depth fell
back in the worker: generated configuration instead contained 72 hours,
16 active agents, adverse/favorable scenarios, five ensembles and Standard.
The run UI clamped requested two rounds to ten and ran both platforms. The
partial historical report used Prediction/Standard. Not every setting failed.

Current path: browser selection → request `prediction_settings` → validation →
saved preparation state → worker argument → generated config → explicit start
platform/round/seed/memory parameters. Supported settings are visible before
Start. Entity/profile caps, single-platform selection, baseline scenario,
ensemble count, depth and the active-agent bounds have regression coverage.
Fast depth disables report interviews, limits tool calls, and permits up to one
reflection; it is not a promise of zero reflection. Both legacy platform panels
and some dual-platform log wording remain even with one platform selected;
the effective settings show which platform executes.

## Implemented request and recovery contract

The [execution contract](../workflow-execution.md) was recorded before its
implementation. [WorkflowLedger](../../backend/app/services/workflow_execution.py)
and [HTTP controls](../../backend/app/api/execution.py) persist the provider,
model, endpoint identity, frozen input fingerprint, authorization history,
request ceiling, deadline and attempt receipts in SQLite.

Every physical attempt reserves one request immediately before transport under
an atomic transaction. Concurrent graph/profile threads and OASIS children
share the same ledger and attempt context. SDK hidden retries are disabled;
supported retries are counted. Failures, timeouts and uncertain delivery consume
allowance without refunds. Usage remains measured or unknown, never invented
zero. Admission and publication share the owned-task cross-process gate.

The fresh clock starts at the first admitted request and includes review pauses.
The last admitted response may publish after a request-count limit, but cannot
schedule another call. Stop, time expiry, superseded authorization and stale
ownership reject late publication. Stop cannot guarantee reversal of provider
billing. Explicit reauthorization retains counts/history, requires a higher
total ceiling, fences the previous epoch and requires acknowledgement of
unfinished attempts. Its newly authorized deadline begins at reauthorization.
Refresh, polling and ordinary retry provide no new spending authorization.

Unscoped production generation is rejected. Local Ollama embeddings are the
supported non-billable embedding path. Secondary generation/boost providers,
remote embeddings and enabled Jev paths are excluded from this authorization
contract. Root/proposal idempotency and immutable revisions remain enforced.
This implements request/time limits, not a monetary billing ceiling.

## Exact-candidate verification

All final results below belong to `34ad6d2`. Earlier intermediate logs keep their
original counts and are not substituted for final results. Providers were
synthetic or explicitly blocked; no real generation calls were made.

| Check | Result and scope |
| --- | --- |
| `UV_PYTHON=3.11 npm run check` | **PASS:** 496 backend, 12 Node and 37 Vitest tests (545 total); production build 3.41 seconds. [Full receipt](evidence/2026-10-03-control-recovery/check-delivery-candidate.txt). Existing locked dependencies; Python 3.11.15, Node 24.21.0, uv 0.11.14. |
| Deterministic evaluations | **PASS:** 168 collected IDs × three runs = 504 passing executions, no missing observations. Correctly blocked workflows count as passing safety assertions, not successful drafts. Four human packets remain unreviewed; all model quality, cost and effort metrics remain null. [Results](evidence/2026-10-03-control-recovery/evaluations-result.json). |
| H1 two-process recovery | **PASS:** exited writer's persisted graph task recovered as Failed, `ownership_lease_expired`, in 30.05 seconds. [Receipt](evidence/2026-10-03-control-recovery/h1-final.txt). |
| Synthetic backup/restore | **PASS:** quiesced SQLite plus 26 complete artifact files; fresh-process restore, immutable/idempotent acceptance, matching parent hashes, two expired owners repaired, newer valid lease preserved. Neo4j backup, hot backup, relocation and power loss are outside this check. [Results](evidence/2026-10-03-control-recovery/backup-result.json). |
| Automated built-UI workflow | **PASS:** 12/12 checks; 24 stage/width snapshots at 375/768/1440px; no detected axe violations, clipped controls or uncaught page errors. Real API/SQLite proposal acceptance and child reopen retain the parent. Generation stages are explicitly substituted. [Results](evidence/2026-10-03-control-recovery/browser-workflow/results.json). |
| Separate browser regressions | **PASS:** 10/10; dialog checks at three widths, focus/Escape, unknown metrics, actual abandoned-owner HTTP recovery and manual retry. Rerun on a separate fixture backend to avoid interference from concurrent workflow tests. [Results](evidence/2026-10-03-control-recovery/browser-regressions/results.json). |
| Visible desktop review | **PASS within synthetic scope:** explicit Start/Stop, refresh preserves Stopped, source proposal review, save as separate revision, reload and inspect ledger. Parent hash receipt remains unchanged. [Receipt](evidence/2026-10-03-control-recovery/visible/receipt.json), [reopened screenshot](evidence/2026-10-03-control-recovery/visible/accepted-revision-reopened.jpg). |
| Dependency/configuration checks | Root and frontend `npm audit`: **zero reported vulnerabilities**. `uv pip check`: 146 compatible packages. Compose CPU and GPU configurations parse with a disposable synthetic `.env`. These are not Python/container CVE scans or image startup checks. [Compose](evidence/2026-10-03-control-recovery/compose-validation-isolated.json). |
| Independent AI review | No actionable blockers within the final narrow review; four targeted regressions independently passed with provider fencing. Source unchanged by reviewer. [Review and limitations](evidence/2026-10-03-control-recovery/independent-review.md). |
| Documentation/evidence | Local links, JSON/XML receipts, image formats, candidate/test-input/bundle hashes, frozen acceptance packet, 34 historical files and five main overlays verified. [Receipt](evidence/2026-10-03-control-recovery/documentation-checks.json) and [evidence manifest](evidence/2026-10-03-control-recovery/manifest.json). Raw failure receipts retain their original whitespace; maintained documentation passes its scoped check. |

Browser substitutions include ontology, graph builder/storage, scenario and
simulation endpoints, a seeded root report/intercepted generation response,
scripted drafting, and blocked external fonts. Injected 409/400/503 responses and
one lost acceptance response exercise error/retry handling; their console/network
entries are expected, so this is not a zero-console-message claim. There is no
historical visual comparison or exhaustive accessibility certification.
Dialog scans retain incomplete color-contrast findings for overlapping/icon
elements; scoped computed text contrast passed, but incomplete findings are
not accessibility passes. Laboratory
LCP was 180ms and CLS 0.230; representative INP and field Core Web Vitals are not
measured, and these values do not constitute a performance pass.

The visible synthetic child is left open at
`http://127.0.0.1:18750/report/report_6b0ffc17d1cb46148ffc1481da4bafe9`.
Its banner discloses fixtures and zero external inference. The displayed score
85 is an unreviewed heuristic, not factual-quality evidence. The
synthetic workflow's 30-minute clock subsequently expired while documentation
was prepared; the saved child remains reviewable with `runtime_limit`, three
counted synthetic attempts, zero in-flight attempts and new calls blocked.
The disabled Stop button at that point is expected terminal behavior.
Eight other owned
synthetic previews were stopped; their logs were preserved outside Git. The
original application, relay and Neo4j services were not stopped or changed.

## Remaining blockers and next action

1. **New live authorization:** the earlier 30-request/15-minute allowance is
   exhausted. No further MiniMax calls are permitted by that approval.
2. **Fresh actual-generation acceptance:** upload → graph → scenario → OASIS →
   completed report → proposal review → test acceptance/reopen has never passed
   in a fresh run on this candidate. Use the [prepared visible plan](../visible-browser-acceptance.md)
   without later-stage seeding or interception.
3. **Quality and retrieval:** historical personas invented unsupported details;
   the outline misdescribed the partial simulation. Historical Neo4j startup
   lacked vector/fulltext indexes and report context fell back to graph records.
   Verify readiness before new generation and review source versus simulation
   claims. No quality improvement is inferred from control repairs.
4. **Candidate operational coverage:** clean installation, new Docker image/
   startup, real Neo4j/OASIS integration and exact-candidate remote CI were not
   run for `34ad6d2`. Previous `242b899` evidence does not satisfy them. No
   lint/type/coverage or Python/container vulnerability scan is claimed.
5. **Recovery limits:** preserved partial artifacts can support an isolated
   manual recovery only after source/graph scope is restored and authorization
   explicitly attached. Legacy interviews and exact-round OASIS continuation
   are not supported recovery promises. Cross-store online backup, active-task
   relocation and lossless memory remain open.

The ready plan freezes the fictional source and original requirement, proposes
60 physical requests/30 minutes for a separate fresh MiniMax-M3 run, and prices
explicit token assumptions. Recovery on a copy has a separate proposed allowance
and retains the original 30 consumed requests. Neither proposal is authorized
or executed. This is a local control-repair milestone, not release readiness
or a passed full live workflow.
