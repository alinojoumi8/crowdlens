# CrowdLens Roadmap

Reconciled 2026-10-03 against application candidate `7f4d68e`, routes, persistence,
tests and [fresh actual MiniMax acceptance](docs/audits/2026-10-03-report-reliability.md).
The unchanged-candidate fictional workflow completed through source proposal,
local test revision acceptance and reload/history reopen, with originals preserved.
Previous [live tests](docs/audits/2026-10-03-live-cedarbrook.md), [control repairs](docs/audits/2026-10-03-control-recovery.md)
and [ECC handoff](docs/audits/2026-10-02-ecc-milestones-3-5.md) retain their separate
candidate identities. This is a prioritized capability backlog, not release dates
or a quality certification. See [the capability manifest](docs/product-capabilities.md).

## Current state

The source implements upload → graph → scenario → simulation → report → proposal
review, using Neo4j, SQLite, and filesystem artifacts. Ollama can keep generation
and embeddings local; hosted providers, website ingestion, and enabled market
lookups use the network. The historical bike-lane browser served hosted generation
on `242b899`; it differs from the new repair candidate and remains unchanged.
Current production/deployment equivalence remains unverified.

| Capability | Current status | Remaining boundary |
| --- | --- | --- |
| Document/URL ingestion and case versions | Implemented; fictional Markdown ingestion exercised live | Other formats/URLs and independent extraction/source fidelity checks. |
| Neo4j graph build, provenance and embedding readiness | Implemented; actual graph build and original-source proposal retrieval exercised | Independent retrieval/source-fidelity evaluation; owned-task recovery is separate. |
| Scenario profiles/settings, simulation and ensembles | Implemented; four named profiles, two Twitter rounds, origin counts and effective settings verified | Broader lifecycle/memory/ensemble quality and independent persona fidelity. |
| Root reports, progress, resume and section regeneration | Implemented; fresh three-section report with frozen original/action provenance and forecast authority | Independently labelled semantic support, omissions and forecast calibration; broader recovery paths. |
| Source-scoped proposals and immutable revisions | Implemented; fresh actual proposal accepted/reopened with private response diagnostics and parent unchanged | Cross-packet contract reliability and independent source/claim quality. |
| `/api/status` readiness endpoint | Implemented | Disk usage and actual generation-provider readiness are not reported/probed. |
| Agent memory persistence | Partial | File-backed short memory/summaries and optional graph memories exist; lossless restart continuity is unverified. |
| Automated checks | Implemented | Frozen-candidate results are in the ECC handoff; deterministic checks do not establish full model E2E or factual quality. |
| Provider selection | Partial | Local/OpenAI-compatible/Anthropic adapters and Ollama/Gemini embeddings exist; per-task routing and broader backend compatibility remain future work. |
| Workflow request/time controls and Stop | Implemented; fresh acceptance and all stopped partial-attempt ledgers retained | Monetary admission and broader provider accounting remain planned. |
| Graph visualization and comparison | Partial | Visualization and case-version comparison exist; whole-graph snapshots, temporal views, and simulation graph diffs remain future work. |

## Next: verify the existing product

### P1 — deployment, full workflow, and evidence quality

- [x] Establish the historical bike-lane browser's commit/image/source fingerprint and preserve its original evidence. See [runtime identity and accounting](docs/audits/2026-10-03-control-recovery.md).
- [ ] Reconcile a chosen deployed revision with the intended source under a separately authorized deployment task.
- [x] Exercise a bounded fictional document through actual upload, graph, scenario, OASIS, report and proposal review with visible MiniMax generation. [Real results](docs/audits/2026-10-03-live-cedarbrook.md) distinguish the repaired/reopened journey from the fresh blocked run; all original hashes remain intact.
- [x] Repair source/action provenance, exact quotation checks and one frozen forecast authority; bounded invalid-passage correction keeps the guards. See [the reliability audit](docs/audits/2026-10-03-report-reliability.md). Semantic quality remains independently unmeasured.
- [x] Preserve completion/parsed audit snapshots and precise contract findings; reproduce failures and complete one fresh proposal acceptance/reopen without weakening guards. Cross-packet reliability remains open.
- [ ] Measure source attribution, unsupported claims, omissions, and reviewer effort on approved held-out packets with independent labels. [Four actual-model drafts are collected](docs/evaluations/2026-10-03-source-review-v2.md), with 0/4 ready and human review pending. Synthetic output and unreviewed drafts are not quality evidence.
- [x] Add limited trace regressions for the retained Round 1 contradiction and carry the unresolved conditional-symmetry premise into current review. Historical files remain unchanged; [semantic review](docs/audits/2026-10-03-semantic-review.md) exposes evidence and coverage limits. Independent entailment/omission labels remain pending.

### P2 — recovery and user experience

- [x] Audit agent/tool/source-scope boundaries and repair reproduced high-priority failures, including owned-task recovery, duplicate root admission, preparation readiness, and stale ensemble cleanup. See [audit follow-ups](docs/audits/2026-10-02-h1-integration-review.md).
- [x] Define and enforce whole-workflow physical-request/time limits, counted retries, Stop, explicit recovery authorization and retained partial outputs. [Contract](docs/workflow-execution.md) and [synthetic verification](docs/audits/2026-10-03-control-recovery.md) cover concurrent admission, restart, delayed responses and terminal polling.
- [ ] Define monetary admission before promising a dollar ceiling; measured tokens, pricing estimates and request/time limits do not establish one.
- [ ] Verify subprocess restart, failed writes, optional graph memory, and forced-run cleanup. Define the memory retention and continuation promise before strengthening it.
- [x] Verify supported report/proposal states in the built UI at 375/768/1440px: keyboard/focus, blocked/stale proposals, lost acceptance response/retry, reopen, unknown metrics, and real owned-task failure/manual retry. [QA evidence](docs/audits/2026-10-02-milestone4-browser-qa.md) identifies all seeded and substituted stages.
- [x] Complete the [fresh visible-browser acceptance plan](docs/visible-browser-acceptance.md) on `7f4d68e` through local test revision acceptance/reload/history. No generation was seeded or substituted. Historical-copy paid recovery remains separate and was not run.
- [x] Rehearse cold synthetic SQLite/artifact restore, same-root expired-task recovery, and separate Neo4j dump/load into new volumes.
- [ ] Define retention/deletion ownership and coordinated cross-store backup procedures; online atomic backup and active-task relocation remain unverified.
- [ ] Promote only after exact-candidate remote CI and explicitly authorized deployment verification. Local clean-install, audit, build, recovery, and image results are recorded in the [release evidence](docs/audits/2026-10-02-milestone5-release-verification.md).

## Stability and performance backlog

- [ ] Verify Python 3.12+ compatibility for the pinned CAMEL/OASIS dependency set; retain Python 3.11 as the verified baseline until then.
- [ ] Add GPU auto-detection if needed; current Compose uses an explicit GPU override with CPU-compatible defaults.
- [ ] Verify transient Neo4j reconnect behavior before adding or promising resilience changes.
- [ ] Extend status with disk capacity and a separately defined generation-provider readiness check.
- [ ] Add optional JSON structured logging; request IDs and timing logs already exist.
- [ ] Measure throughput, memory use, latency, and model calls per workload/hardware tier before setting performance targets.

## Retrieval and model improvements

- [ ] Evaluate configurable hybrid-search weights per graph against a fixed retrieval baseline.
- [ ] Evaluate graph-aware reranking; existing advisory reranking is not evidence of a quality gain.
- [ ] Verify additional embedding models/providers, dimensions, migration and re-embedding behavior. Existing provider selection does not prove every model works.
- [ ] Evaluate temporal edge weighting/decay with source-versus-simulation provenance intact.
- [ ] Add per-task model routing if measured latency/quality justifies it.
- [ ] Verify vLLM/llama.cpp compatibility before listing them as supported backends.
- [ ] Benchmark entity/relation extraction across models on held-out source text.
- [ ] Add hardware-aware context/quantization configuration after measuring actual constraints.

## Simulation and graph exploration

- [ ] Add WebSocket progress if existing polling is insufficient; current dashboards already expose progress via polling.
- [ ] Define custom agent-archetype and multilingual simulation contracts, including quality evaluations.
- [ ] Provide a documented consolidated transcript-export format; action/log APIs and artifact files already exist.
- [ ] Evaluate community detection and visualization/filtering improvements against current graph UI behavior.
- [ ] Define temporal relationship views and side-by-side simulation graph diffs.
- [ ] Define whole-graph snapshot/restore independently from existing case-document versions.

## Optional product expansion

These items require a separate capability contract and product decision. They are
not prerequisites for the current single-operator local workflow.

- [ ] Authentication, tenant isolation, and multi-user deployment.
- [ ] Plugin interfaces for extraction, retrieval, and report templates.
- [ ] Kubernetes/Helm packaging for an explicitly chosen hosted deployment.
- [ ] Federation between instances with explicit sharing and provenance rules.
- [ ] Fine-tuned local extraction models, justified by independent quality evidence.
- [ ] Voice interaction and a mobile companion application.

## Hardware guidance

Hardware/model combinations are sizing starting points, not benchmarked quality
or speed tiers. Context size, quantization, workload and model concurrency affect
memory use and latency. Use the [README hardware guidance](README.md) to plan a
local setup, then measure a fixed workload before promising performance.

## Contributing

The project is AGPL-3.0 licensed. Useful contributions include verified runtime
compatibility, recovery tests, source-quality evaluations, retrieval measurements,
and documentation. See [GitHub Issues](https://github.com/alinojoumi8/crowdlens/issues)
for tracked work and [the ECC workflow](docs/ECC-WORKFLOW-PLAN.md) for delivery steps.

### Source coverage repair follow-up

[Source coverage and summary repair](docs/audits/2026-10-03-source-coverage-repair.md) implements bounded companion-document retrieval, source metadata preservation, planned-claim coverage and server-resolved exact summary spans. Final check passes 673 tests and build. Fresh v3 actual MiniMax verification retrieved all eight current originals, with one ready and three blocked proposals after 11 requests; strict guards and original reports are preserved. Independent Astra max review finds all 28 material section facts covered; 31 of 33 claim judgments are supported, one unsupported and one ambiguous. These AI opinions stay separate from still-unmeasured human labels/time. This does not establish broad factual quality or release readiness.

## Claim grounding and summary contract follow-up — 2026-10-04

[Contract completion](docs/audits/2026-10-04-draft-contract-completion.md) requires complete explicit AI source judgments, checks resulting-summary consistency even with edits, and confines server-owned summary replacements to a unique literal selected-section span. Unmapped summaries stay unchanged for review; strict legacy contracts remain compatible. Title-topic retrieval and raw target exports are covered by separate regressions. All 694 tests and the build pass, with independent code review and a visible provider-disabled immutable-revision test. Fresh MiniMax v4/v5 each retain 0 ready out of four attempts (8/10 requests); v5 retrieves all eight originals and preserves all parents, but actual-model JSON, premise and semantic-audit reliability remain unresolved. Human labels/time remain unmeasured. These scoped fixes do not establish factual certification, end-to-end or release readiness. Next: separate development work on provider contract and audit reliability, then new frozen verification cases.

## Output reliability follow-up — 2026-10-05

[JSON, summary and explicit audit contracts](docs/audits/2026-10-05-output-reliability.md) now build default summary wording from selected ledger claims, retain one counted syntax correction per phase, and require complete claim/paragraph/edit/document judgments for fresh proposals. Mixed or missing protocols and negative judgments block. Final check: 713 tests/build and independent code review pass. Fresh v6 MiniMax verification retains 4/4 ready proposals, 12 requests, all eight originals and unchanged parents; the final stricter gate revalidates those retained audits without rerunning v6. Astra max covers all 22 material facts and rates 24 of 25 claims supported, but flags one conditional-to-universal inference also repeated in its summary. Ready remains reviewable, not factual approval. Human ratings/time remain unmeasured; no actual proposal was accepted or published. Followed by the conditional-correction and completion milestones below.

Conditional-offer correction (2026-10-05): exact source extraction and acceptance guards prevent detected offer conditions being rewritten as prerequisites; 728 tests/build pass. Fresh v7 attempts were 0/2 ready (both conservatively blocked). A separate Elmreach correction received source-first AI support for all four claims; original evidence remains frozen. See [audit](docs/audits/2026-10-05-conditional-fidelity.md).

Conditional completion (2026-10-05): server-owned complete source excerpts avoid guarded paraphrase false positives; 752 tests/build and independent code review pass. Two ready development drafts received source-first AI support (7/7 claims, 10/10 material facts); all eight development attempts remain counted. Frozen v8 stays 0/2 ready due ordinary draft omissions and no source anchor. No publication or release-readiness claim. See [audit](docs/audits/2026-10-05-conditional-completion.md).

Focused correction and participant selection follow-up (2026-10-10): implemented
literal date/number proposals and persisted type-aware capped selection. Browser QA
saved a narrow corrected revision and prepared six profiles including both labelled
sides. Existing simulation activity and forecast calibration remain unchanged.
Next: verify actual activity across both sides and held-out ambiguous correction
cases. See [receipt](docs/audits/2026-10-10-focused-correction-participants.md).


Bounded wording correction follow-up: added single-occurrence source-backed
wording proposals with explicit before/after review, source snapshots and blocked
adoption for unsupported/unverified audits. Synthetic regression cases cover
page/date confusion, remote-oath locations and oversized source transcription.
Semantic accuracy still depends on fallible source review; high structural
scores do not certify facts.

Wording correction and longer-run verification: [receipt](docs/audits/2026-10-10-wording-corrections.md).
