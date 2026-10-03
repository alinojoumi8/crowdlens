# CrowdLens visible-browser acceptance plan and results

Current result: **fresh visible-browser acceptance completed on `7f4d68e`**.
[The reliability audit](audits/2026-10-03-report-reliability.md) records actual
MiniMax-M3 upload → graph → four personas → two Twitter rounds → root report →
source proposal → local test revision acceptance → reload/history reopen. The
new child `report_3d12d343d6fa4c5d86998d8d88ea042a` remains Needs review and the parent is unchanged. One 90-request/
60-minute window stopped at 26 completed requests, with zero in-flight/unknown
attempts. Five stopped intermediate candidates used 87 requests separately.
Source, settings, compiled frontend and application candidate stayed unchanged
through this final run. Generation was not seeded or substituted. Independent
quality and exact-candidate release/deployment verification remain open.

## Historical preparation and earlier results

Prepared 2026-10-03 for tested source `34ad6d27e298f33317e443f0123143fa5e865eab`,
fingerprint `fea6ca781b9a175fe9face0055dc195bf7f685551e5af5a5f2b42a5342450006`.
The user subsequently approved MiniMax usage as needed, including M3.1 Flash;
only `MiniMax-M3` was used. The [actual browser audit](audits/2026-10-03-live-cedarbrook.md)
records three repairs and final source `1f61571`, fingerprint
`f72be2d03b85a404abf19992ddf2d86a703848bc50dbe87cf519d8c18a25333f`.
The first journey saved/reopened a revision after source changes (42 requests).
A separate fresh run on the frozen final source completed its report but all
three proposals blocked (38 requests). **That earlier fresh acceptance attempt remained incomplete.**
Both workflows are stopped; no further call is pending.

The earlier exhausted 30-request/15-minute allowance was not reused.
[Control repair evidence](audits/2026-10-03-control-recovery.md) and
[historical accounting](audits/2026-10-03-bike-lane-request-accounting.md)
retain their separate synthetic and incomplete historical-live boundaries.

## Frozen fresh input and settings

Use [cedarbrook-bike-lane.md](acceptance-fixtures/cedarbrook-bike-lane/cedarbrook-bike-lane.md)
unchanged and the [original requirement](acceptance-fixtures/cedarbrook-bike-lane/requirement.txt).
The four people, municipality and proposed pilot are fictional. No URL ingestion,
real personal documents, external market lookup or other source is included.

- Source SHA-256: `1d79d4a96e4af613f81a1a9195a277ee15753a154d6e2daf48ddd7fae4aaf48b`.
- Authorized input fingerprint: `a0cbc3c1a4d5e82a5c02fd14cddc9d7c568b88386b586f5e291a4b26ac568cd4`.
- [Manifest](acceptance-fixtures/cedarbrook-bike-lane/manifest.json) binds the
  filename, exact bytes, requirement and empty URL list. Changing any of these
  requires a fresh matching input approval and authorization operation.
- A review copy is ready at
  `/home/ali/Documents/CrowdLens-reviews/2026-10-03-control-recovery/fresh-inputs/`.

[Planned settings JSON](acceptance-fixtures/cedarbrook-bike-lane/effective-settings.json)
contains the requested overrides. Actual saved settings and worker behavior were
checked separately; the table incorporates observed limitations:

| Setting | Fresh live test value |
| --- | --- |
| Provider/model/transport | MiniMax / `MiniMax-M3` / Anthropic Messages; Standard tier; primary generation only |
| Endpoint | `https://api.minimax.io/anthropic`, isolated test process configuration |
| Agent/profile scope | Four profiles, profile parallelism one; use the native Agent types selection to include the types of Maya, Leo, Priya and Daniel and exclude the municipality; generated type labels can vary |
| Scenario | Baseline; one ensemble run |
| Time/activation | Two simulated hours, 60 minutes/round, one active agent per round/hour; two maximum rounds |
| Platform/seed | Twitter only; seed 42 (does not make hosted model output deterministic) |
| Memory | Off; graph-memory updates disabled |
| Report | General Prediction / Fast; source facts, simulated discussion, uncertainties requested as three sections |
| Report work | Fast allows up to two tools per section and one reflection; interviews disabled. The planned `REPORT_AGENT_MAX_TOOL_CALLS=1` environment value is not read/enforced |
| Transport | No automatic retries for the controlled live test; any explicit retry still consumes the aggregate allowance |
| Embeddings | Existing local Ollama `nomic-embed-text`; auto-pull disabled |
| Other paths | Jev off, market provider none, no boost/secondary provider, remote embeddings or provider server tools |

The internal preset identifier remains a compatibility field; inspect all saved
overrides and effective values before Start. The fresh stored availability flags
include both platforms and its CLI maximum is 72, while actual Twitter-only
execution clamps to the duration-derived two rounds. Generated 48-hour reasoning
and legacy active-hour aliases disagree with effective bounds; these remain
metadata findings. If four named source entities are
not selectable or preparation disagrees with these bounds, stop and report the
mismatch instead of substituting seeded profiles. Outline section count is
model generated; record any departure from the requested three sections.

## Preflight and isolated setup

1. Preserve explicit provider/input authorization before live generation. The
   later user approval satisfied this prerequisite for the executed tests;
   the authorization text below is the historical planning template.
2. Launch an isolated instance of the tested source with new SQLite/artifact
   roots and a fresh Neo4j database/container. Existing app, old relay, databases,
   volumes, global provider settings and original review artifacts stay intact.
   Record source revision/tree, fingerprint, frontend bundle hashes, process/image
   and non-secret configuration. If code changes, reverify the candidate first.
3. Wait for Neo4j readiness before application initialization. Verify source
   graph indexes, local embedding availability and status/embedding readiness;
   the historical run had only lookup indexes and empty report search context.
   A failed readiness check is a blocker, not a reason to seed later outputs or
   silently enable degraded generation. No new model download is included.
4. Open the new loopback URL in a **visible desktop browser** and keep major
   stages on screen. The synthetic preview at `127.0.0.1:18750` is only a review
   deliverable; do not reuse its seeded data or generation substitutes for this
   test. Record the newly assigned URL before beginning.
5. Inspect the authorization dialog against the frozen file/requirement and
   select a bounded request/time allowance under the existing human approval.
   The first workflow used 60 requests; the separate fresh workflow used 45;
   both used 1,800-second admission windows. One durable workflow ID must follow
   each workflow's generated resources.

## Fresh actual-generation acceptance

Perform the actual UI workflow; no seeded reports, personas or simulation
outputs and no intercepted generation responses. Screenshots/recordings supplement
the visible browser rather than replace it. Refresh checks must be read-only;
no duplicate Prepare/Start/Generate request is permitted on reopen.

| Visible stage | Action and required evidence |
| --- | --- |
| Upload → ontology | Upload the frozen file and paste the exact frozen requirement. Use actual generation. Record project/case/version/workflow/task IDs, stage receipts, source and authorized-input hashes. Refresh and verify no new automatic generation. |
| Source graph | Build with the real provider and Neo4j. Inspect the four named source participants, source chunks and readiness. Preserve exact graph scope and document locators. Distinguish generated relations from documentary claims. |
| Scenario | Select supported General Prediction/Fast and the explicit settings above. Prepare actual personas/configuration. Compare browser payload, stored preparation settings, generated config and displayed effective values; four profiles and limits must agree. Record invented persona details as quality findings. |
| Simulation | Explicit Start; actual OASIS child, Twitter only, at most two rounds with one active agent and memory off. Inspect actions and request receipts. Refresh without automatic restart. Record terminal reason and actual completed rounds, not process exit alone. |
| Root report | Explicitly generate Fast using actual source/graph/simulation retrieval. Show progress, sources and terminal state. Record outline/section counts, evidence origin, citations, usage, attempts and elapsed time. Request allowance must not reset. A terminal failure/limit remains partial, not a passed stage. |
| Original preservation | When the root report is saved and eligible for proposals, freeze all root report file hashes, section hashes and identity/scope. Display and retain review warnings; a quality heuristic does not establish accuracy. |
| Proposal review | Choose an eligible source-related section and use **Draft with sources** with the actual provider. Keep before/after, summary edits, original excerpts, claim ledger and limitations visible. Record proposal ID/digest/source scope and consumed requests. A safe blocked result is a control success but not a completed proposal journey. |
| Test revision acceptance | After inspecting the proposal, **Save as new revision** for this fictional test. Acceptance runs no generation and is already part of the requested acceptance scope. Record child/parent IDs, immutable manifest and Needs review state. No publication outside the local test is included. |
| Reopen | Reload the child and open it again from history. Verify child content/ledger persists, unselected sections are unchanged and the original hashes still match. Repeated acceptance with the same digest must return one child without a new provider request. |
| Handoff | Leave the generated report/proposal or accepted child open in the visible browser. Preserve screenshots, IDs, timestamps, ledger and original/child hashes under a new dated review directory. Report actual stage completion and separate quality findings. |

The successful fresh-run criterion is actual generation through report and
proposal review, followed by accepted child reopening with the parent preserved.
If a model contradicts the fictional source, preserve the output and report the
finding. Do not silently repair or regenerate it to manufacture a pass.

Stop and exhaustion already have synthetic regression evidence. Do not deliberately
interrupt the sole fresh completion attempt solely to repeat those probes. If
the user requests Stop, settings differ, or a control fails, Stop immediately,
preserve partial output, inspect in-flight/unknown requests and verify no new
admissions. Count all stages/children/retries together. At the chosen request ceiling or the
deadline, stop scheduling; do not extend the allowance, restart with a fresh
ledger, or call a partial/recovered run a fresh pass. Review pauses are inside
the 30-minute clock starting at first admission. In the first repair journey,
explicit window renewals under the user's broader approval retained all
consumption; that mixed-candidate journey is not the fresh acceptance result.
The separate fresh run had one epoch, no renewal, and stopped at 38/45 requests
after 1,459.203 seconds. No generation was resumed by polling or refresh.

## Executed outcomes

The [dated audit](audits/2026-10-03-live-cedarbrook.md) and its selected evidence
record actual generation without fixture substitution. Both journeys reached
real graphs, four source participants, two Twitter rounds and three-section
root reports. The first saved child `report_561a7739a24d480bb5a0ac086eec2cdf`
remains Needs review; reload/history and repeated acceptance preserved one child
and unchanged parent files. It used several source revisions during repairs.

The fresh frozen-candidate root `report_6ad447817a9b` remains completed, with
three retained blocked drafts: `invalid_audit`, `paragraph_kind_mismatch`, then
`invalid_audit` on a different section. Saving remained disabled and no child
was accepted. The original raw audit JSON is not persisted, so its exact invalid
field cannot be reconstructed. This is a safely blocked control outcome and an
incomplete fresh acceptance journey. Source/trace provenance and conflicting
prose versus forecast probabilities are separate report-quality findings.

## Separate recovery on preserved copies

The copy and SHA manifest are prepared at
`/home/ali/Documents/CrowdLens-reviews/2026-10-03-control-recovery/recovery-inputs/`
and `recovery-inputs-sha256.json`. It contains the frozen interrupted report,
simulation artifacts and control DB plus original source. No paid recovery has
run. This exercise is independent of fresh-run acceptance.

1. Use another isolated working copy of this preserved copy, keeping a manifest
   before mutation. Restore matching original source chunks/graph scope using
   the read-only historical graph evidence into a new database; do not point the
   recovery worker at the original database. Verify required source evidence and
   local indexes. If exact scope cannot be restored, report recovery blocked.
2. Legacy absolute artifact roots and task bindings need explicit migration to
   this isolated destination; active-task relocation is not established. Do not
   promise automatic recovery by merely moving a SQLite file. Inspect/reconcile
   legacy task uncertainty before accepting any new generation.
3. Following separate recovery approval, attach existing project
   `proj_e3b124fe4834`, simulation `sim_c59433035846` and report
   `report_8c343d6450c0` with `POST /api/execution/authorize`, the selected
   provider/model, `consumed_requests: 30`, `max_requests: 60`, `max_seconds: 1800`,
   a unique request key, `confirmed: true` and explicit resources. Preserve the
   original receipt file alongside the imported count. This is 30 additional
   attempts, not a reset to zero. Do not execute this POST before approval.
4. Open the partial report in the visible browser. Progress must return a
   structured terminal response; refresh must not restart work. Only explicit
   Resume or permitted section regeneration may generate. Select Fast for a new
   attempt where supported; retain the old Standard-depth metadata in the archive.
   Disable interviews because historical IPC cannot satisfy new workflow/epoch
   ownership. Do not automatically rerun the falsely Completed simulation.
5. Preserve the interrupted outline/evidence, any resumed sections, failure
   reason, ledger and unknown usage. If recovery completes, proposal/test revision
   review is bounded by the same extra allowance. Keep it labelled recovery on
   copies; it never supplies evidence of fresh upload-to-proposal completion.

## Historical proposed authorization and cost

This section preserves the proposal written before the user's later broader
approval. It is not a request for another approval of the completed tests.

**Original fresh-run proposal:** MiniMax-M3 at the Standard Anthropic endpoint,
only the frozen fictional Cedarbrook packet/requirement and its derived graph,
personas, simulated discussion, report and proposal context; **60 total physical
model attempts and 30 minutes from first admission**, all stages/children/retries
and review pauses included. Use existing local embeddings and the exact supported
settings above. No automatic extension, other provider, download or deployment.

**Original optional-recovery proposal:** the same provider and fictional
scope, only isolated copies of the preserved partial run, **at most 30 additional
attempts**, imported original count 30/new total ceiling 60, and a fresh
30-minute recovery window. Approval of the fresh run alone does not approve this.

Historical preparation consumed nine requests, then memory updates and the
larger dual-platform simulation consumed 19, leaving only two for the report.
The proposed memory-off/two-round/single-platform run removes that major known
consumer. A planning breakdown is nine preparation, about two simulation,
roughly 8–13 report and 3–10 proposal calls, leaving reserve within 60. This was
an estimate, not a completion guarantee. Each actual root consumed 19 requests,
exceeding that report estimate. The unchanged-candidate journey used two
ontology/graph calls, seven preparation calls, two simulation calls, 19 report
calls and eight proposal calls: 38 total. Its time/request allowance was adequate
for those attempts, but model response-contract failures prevented acceptance.

Published Standard M3 rates checked 2026-10-03 are USD $0.30/M input and $1.20/M
output tokens at ≤512k input per request; cache reads are $0.06/M.
[Official pricing](https://platform.minimax.io/docs/pricing/overview).
At a planning assumption of 16k input and 8k output for every one of 60 attempts,
the calculation is `60 × (16,000 × 0.30 + 8,000 × 1.20) / 1,000,000 = $0.864`.
Approximately **USD $1 is a planning estimate**, with no cache discount assumed.
It is not an implemented dollar ceiling, provider invoice or guaranteed maximum.
Actual larger prompts/output, different account terms or unknown in-flight usage
can cost more. If a strict monetary cap is required, establish provider-side
controls or a separate monetary-admission contract before testing.

Historical suggested approval text:

> Authorize one fresh visible-browser CrowdLens test using MiniMax-M3 Standard
> and the frozen fictional Cedarbrook packet in this plan, with at most 60
> physical model requests and 30 minutes from first admission across all stages.
> Use the documented memory-off, four-profile, two-round settings. I understand
> the approximately USD $1 estimate is not an enforced dollar cap. Do not extend
> the allowance or run recovery without another approval.

Actual token fields and the stopped 80-request combined ledger are in the dated
audit; the provider invoice amount is unknown. The historical USD $1 estimate
is not the measured bill for either historical journey. The later fresh acceptance
is recorded at the top; independent quality, deployment equivalence and release
readiness remain unestablished.
