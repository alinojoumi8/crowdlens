# CrowdLens Roadmap

Reconciled 2026-10-02 against `main` at `34275b7`, routes, persistence, tests,
and bounded runtime checks. This is a prioritized capability backlog, not a set
of committed release dates. See [the capability manifest](docs/product-capabilities.md)
for contracts and verification evidence.

## Current state

The source implements upload → graph → scenario → simulation → report → proposal
review, using Neo4j, SQLite, and filesystem artifacts. Ollama can keep generation
and embeddings local; hosted providers, website ingestion, and enabled market
lookups use the network. The observed local deployment uses hosted generation
and appears to predate the current source; deployed/source equivalence is unverified.

| Capability | Current status | Remaining boundary |
| --- | --- | --- |
| Document/URL ingestion and case versions | Implemented | Fresh full-pipeline run and extraction/source fidelity checks. |
| Neo4j graph build, provenance and embedding readiness | Implemented | Live build, retrieval-quality and failure-recovery verification. |
| Scenario profiles/settings, simulation and ensembles | Implemented | Real subprocess lifecycle and scenario-quality evidence. |
| Root reports, progress, resume and section regeneration | Implemented | Independent factual/omission review and live generation evidence. |
| Source-scoped proposals and immutable revisions | Implemented; synthetic HTTP lifecycle verified | Current browser checks and real-source quality evaluation. |
| `/api/status` readiness endpoint | Implemented | Disk usage and actual generation-provider readiness are not reported/probed. |
| Agent memory persistence | Partial | File-backed short memory/summaries and optional graph memories exist; lossless restart continuity is unverified. |
| Automated checks | Implemented | 347 backend + 28 frontend tests and build passed in this milestone; complete E2E/quality coverage is unverified. |
| Provider selection | Partial | Local/OpenAI-compatible/Anthropic adapters and Ollama/Gemini embeddings exist; per-task routing and broader backend compatibility remain future work. |
| Graph visualization and comparison | Partial | Visualization and case-version comparison exist; whole-graph snapshots, temporal views, and simulation graph diffs remain future work. |

## Next: verify the existing product

### P1 — deployment, full workflow, and evidence quality

- [ ] Establish the deployed commit/build identity and reconcile it with the intended source revision under a separate deployment task.
- [ ] Run a bounded synthetic document through all six stages with real local services or explicitly authorized hosted inference; record source scope, IDs, timings, retries, and original/revision hashes.
- [ ] Measure source attribution, unsupported claims, omissions, and reviewer effort on approved held-out packets with independent labels. Synthetic model output and unreviewed fixtures are not quality evidence.

### P2 — recovery and user experience

- [ ] Audit agent/tool/retry/source-scope boundaries with ECC `agent-architecture-audit`; fix demonstrated failures with regression tests.
- [ ] Verify subprocess restart, failed writes, optional graph memory, and forced-run cleanup. Define the memory retention and continuation promise before strengthening it.
- [ ] Verify report/proposal workflows in the built UI at desktop/mobile widths, including keyboard navigation, blocked/stale proposals, and interrupted acceptance recovery.
- [ ] Define retention and deletion ownership across SQLite, artifacts, and Neo4j; rehearse a consistent backup/restore on synthetic data.
- [ ] Repeat clean-environment installation, current CI, both dependency audits, Compose validation, and image build for the next release candidate.

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
