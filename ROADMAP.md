# CrowdLens Roadmap

Reconciled 2026-10-03 against control/recovery candidate `34ad6d2`, routes,
persistence, tests, and bounded synthetic runtime checks. The [repair audit](docs/audits/2026-10-03-control-recovery.md)
records its identity and remaining real-model gaps. The earlier [ECC handoff](docs/audits/2026-10-02-ecc-milestones-3-5.md)
retains verification for `242b899` and its separate reporting commit. This is
a prioritized capability backlog, not a set
of committed release dates. See [the capability manifest](docs/product-capabilities.md)
for contracts and verification evidence.

## Current state

The source implements upload → graph → scenario → simulation → report → proposal
review, using Neo4j, SQLite, and filesystem artifacts. Ollama can keep generation
and embeddings local; hosted providers, website ingestion, and enabled market
lookups use the network. The historical bike-lane browser served hosted generation
on `242b899`; it differs from the new repair candidate and remains unchanged.
Current production/deployment equivalence remains unverified.

| Capability | Current status | Remaining boundary |
| --- | --- | --- |
| Document/URL ingestion and case versions | Implemented | Fresh full-pipeline run and extraction/source fidelity checks. |
| Neo4j graph build, provenance and embedding readiness | Implemented | Full model-backed build and retrieval-quality verification; owned-task recovery is verified separately. |
| Scenario profiles/settings, simulation and ensembles | Implemented | Real subprocess lifecycle and scenario-quality evidence. |
| Root reports, progress, resume and section regeneration | Implemented | Independent factual/omission review and live generation evidence. |
| Source-scoped proposals and immutable revisions | Implemented; synthetic HTTP and built-UI lifecycle verified | Real-model and independent human quality evaluation. |
| `/api/status` readiness endpoint | Implemented | Disk usage and actual generation-provider readiness are not reported/probed. |
| Agent memory persistence | Partial | File-backed short memory/summaries and optional graph memories exist; lossless restart continuity is unverified. |
| Automated checks | Implemented | Frozen-candidate results are in the ECC handoff; deterministic checks do not establish full model E2E or factual quality. |
| Provider selection | Partial | Local/OpenAI-compatible/Anthropic adapters and Ollama/Gemini embeddings exist; per-task routing and broader backend compatibility remain future work. |
| Workflow request/time controls and Stop | Implemented; synthetic concurrency/restart/browser regressions verified | Fresh real-provider acceptance, monetary ceiling and broader provider accounting remain unverified or planned. |
| Graph visualization and comparison | Partial | Visualization and case-version comparison exist; whole-graph snapshots, temporal views, and simulation graph diffs remain future work. |

## Next: verify the existing product

### P1 — deployment, full workflow, and evidence quality

- [x] Establish the historical bike-lane browser's commit/image/source fingerprint and preserve its original evidence. See [runtime identity and accounting](docs/audits/2026-10-03-control-recovery.md).
- [ ] Reconcile a chosen deployed revision with the intended source under a separately authorized deployment task.
- [ ] Run a bounded synthetic document through all six stages with real local services or explicitly authorized hosted inference; record source scope, IDs, timings, retries, and original/revision hashes.
- [ ] Measure source attribution, unsupported claims, omissions, and reviewer effort on approved held-out packets with independent labels. Synthetic model output and unreviewed fixtures are not quality evidence.

### P2 — recovery and user experience

- [x] Audit agent/tool/source-scope boundaries and repair reproduced high-priority failures, including owned-task recovery, duplicate root admission, preparation readiness, and stale ensemble cleanup. See [audit follow-ups](docs/audits/2026-10-02-h1-integration-review.md).
- [x] Define and enforce whole-workflow physical-request/time limits, counted retries, Stop, explicit recovery authorization and retained partial outputs. [Contract](docs/workflow-execution.md) and [synthetic verification](docs/audits/2026-10-03-control-recovery.md) cover concurrent admission, restart, delayed responses and terminal polling.
- [ ] Define monetary admission before promising a dollar ceiling; measured tokens, pricing estimates and request/time limits do not establish one.
- [ ] Verify subprocess restart, failed writes, optional graph memory, and forced-run cleanup. Define the memory retention and continuation promise before strengthening it.
- [x] Verify supported report/proposal states in the built UI at 375/768/1440px: keyboard/focus, blocked/stale proposals, lost acceptance response/retry, reopen, unknown metrics, and real owned-task failure/manual retry. [QA evidence](docs/audits/2026-10-02-milestone4-browser-qa.md) identifies all seeded and substituted stages.
- [ ] Execute the [fresh visible-browser acceptance plan](docs/visible-browser-acceptance.md) through actual generation, OASIS, report, proposal, test revision acceptance and reopen after new bounded approval. The previous live allowance is exhausted; recovery on preserved copies is a separate test.
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
