# CrowdLens visible-browser acceptance plan

Prepared 2026-10-03 for tested source `34ad6d27e298f33317e443f0123143fa5e865eab`,
fingerprint `fea6ca781b9a175fe9face0055dc195bf7f685551e5af5a5f2b42a5342450006`.
**Paid execution is not authorized.** The earlier 30-request/15-minute approval
is exhausted. The [control repair audit](audits/2026-10-03-control-recovery.md)
and [prior accounting](audits/2026-10-03-bike-lane-request-accounting.md) separate
passing synthetic controls from the incomplete historical live run.

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

[Effective settings JSON](acceptance-fixtures/cedarbrook-bike-lane/effective-settings.json)
contains explicit overrides, so preset defaults cannot silently expand the run:

| Setting | Fresh live test value |
| --- | --- |
| Provider/model/transport | MiniMax / `MiniMax-M3` / Anthropic Messages; Standard tier; primary generation only |
| Endpoint | `https://api.minimax.io/anthropic`, isolated test process configuration |
| Agent/profile scope | Four profiles, profile parallelism one; review the selected graph entities before preparation |
| Scenario | Baseline; one ensemble run |
| Time/activation | Two simulated hours, 60 minutes/round, one active agent per round/hour; two maximum rounds |
| Platform/seed | Twitter only; seed 42 (does not make hosted model output deterministic) |
| Memory | Off; graph-memory updates disabled |
| Report | General Prediction / Fast; source facts, simulated discussion, uncertainties requested as three sections |
| Report work | Tool allowance one; Fast permits up to one reflection; interviews disabled |
| Transport | No automatic retries for the controlled live test; any explicit retry still consumes the aggregate allowance |
| Embeddings | Existing local Ollama `nomic-embed-text`; auto-pull disabled |
| Other paths | Jev off, market provider none, no boost/secondary provider, remote embeddings or provider server tools |

The internal preset identifier remains a compatibility field; inspect all saved
overrides and effective values before Start. If four named source entities are
not selectable or preparation disagrees with these bounds, stop and report the
mismatch instead of substituting seeded profiles. Outline section count is
model generated; record any departure from the requested three sections.

## Preflight and isolated setup

1. Obtain the exact new authorization below before enabling live generation.
   Preserve it with provider, frozen manifest, request ceiling and runtime.
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
   select 60 physical requests and 1,800 seconds. Confirm only under the separate
   human approval. One durable workflow ID must follow all generated resources.

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
admissions. Count all stages/children/retries together. At 60 attempts or the
deadline, stop scheduling; do not extend the allowance, restart with a fresh
ledger, or call a partial/recovered run a fresh pass. Review pauses are inside
the 30-minute clock starting at first admission.

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

## Proposed authorization and cost

**Fresh run, not yet approved:** MiniMax-M3 at the Standard Anthropic endpoint,
only the frozen fictional Cedarbrook packet/requirement and its derived graph,
personas, simulated discussion, report and proposal context; **60 total physical
model attempts and 30 minutes from first admission**, all stages/children/retries
and review pauses included. Use existing local embeddings and the exact supported
settings above. No automatic extension, other provider, download or deployment.

**Optional recovery, separately approved:** the same provider and fictional
scope, only isolated copies of the preserved partial run, **at most 30 additional
attempts**, imported original count 30/new total ceiling 60, and a fresh
30-minute recovery window. Approval of the fresh run alone does not approve this.

Historical preparation consumed nine requests, then memory updates and the
larger dual-platform simulation consumed 19, leaving only two for the report.
The proposed memory-off/two-round/single-platform run removes that major known
consumer. A planning breakdown is nine preparation, about two simulation,
roughly 8–13 report and 3–10 proposal calls, leaving reserve within 60. This is
an informed estimate: a complete report/proposal has not been measured, OASIS
may make extra calls and model repair loops/latency can consume the reserve.
Sixty requests and 30 minutes are likely sufficient for this small test, not
a completion guarantee.

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

Suggested new approval text:

> Authorize one fresh visible-browser CrowdLens test using MiniMax-M3 Standard
> and the frozen fictional Cedarbrook packet in this plan, with at most 60
> physical model requests and 30 minutes from first admission across all stages.
> Use the documented memory-off, four-profile, two-round settings. I understand
> the approximately USD $1 estimate is not an enforced dollar cap. Do not extend
> the allowance or run recovery without another approval.

This plan prepares execution and review. It does not claim full live workflow
success, independently established model quality, deployment equivalence or
release readiness.
