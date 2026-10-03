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
- [ ] Measure source attribution, unsupported claims, omissions, and reviewer effort on approved held-out packets with independent labels. Synthetic model output and unreviewed fixtures are not quality evidence.
- [ ] Start that semantic milestone with the retained Round 1 contradiction and
  unverified conditional-symmetry premise from the [fresh reliability audit](docs/audits/2026-10-03-report-reliability.md); both escaped mechanical scoring.

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
