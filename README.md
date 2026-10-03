<div align="center">

<img src="./static/image/crowdlens-banner.svg" alt="CrowdLens — Explore how people respond" width="100%"/>

# CrowdLens

**Explore how people respond.**

AI scenario simulation with a local-first runtime, knowledge graphs, and evidence review.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue)](./LICENSE)

</div>

## What is CrowdLens?

CrowdLens turns documents into scenarios populated by AI agents with different
perspectives. Explore public reactions, conversations, and shifts in simulated
sentiment; compare assumptions and inspect the resulting analysis.

Simulation output is generated behavior, not a verified forecast of real people
or markets. Review source attribution and factual claims before using a report
to inform a decision.

The default setup uses Ollama and Neo4j on your hardware. Hosted generation and
embedding providers are optional; enabling them sends the corresponding inputs
to the configured provider. Website ingestion and optional market lookups also
require network access. Choose your configuration to match your data needs.

CrowdLens builds on the work of [666ghj](https://github.com/666ghj) and
[nikmcfly](https://github.com/nikmcfly). The product name
has changed; existing storage paths and Docker service names remain compatible.
See [the rebrand plan and compatibility notes](docs/rebranding.md).

## Workflow

1. **Upload** — Provide PDF, Markdown, or text files and/or website URLs with a scenario requirement. CrowdLens stores source documents, creates project/case-version metadata, and generates an ontology.
2. **Graph** — Build entities, relationships, and source-linked chunks in Neo4j. Inspect graph progress and embedding readiness before continuing.
3. **Scenario** — Select entities and settings, generate agent profiles, and prepare the simulation configuration. Agent count and behavior depend on the sources and settings.
4. **Simulation** — Run agents on the selected simulated platform and inspect effective settings, unique posts, model actions and separately labelled initial/scheduled inputs. Run metadata and artifacts persist; file-backed agent memory and optional Neo4j memory updates do not guarantee complete history or lossless restart continuity.
5. **Report** — Generate a structured analysis with bounded original-source excerpts and actual simulation actions distinguished from graph/persona paraphrases and input posts. New reports save provenance and freeze the forecast before prose so the headline table and panel share one authority. Inspect source evidence and review warnings; mechanical checks and report completion do not certify factual correctness.
6. **Proposal review** — On an eligible saved report, use **Draft with sources** to review a proposed section, summary changes, claim ledger, original excerpts and precise validation findings. Private diagnostics retain completion text and parsed model output. **Save as new revision** preserves the parent and creates a separate immutable report that remains `needs_review`.

Report chat and agent interviews are optional follow-up tools. Agent interviews
require an available simulation environment. See the
[capability manifest](docs/product-capabilities.md) for API contracts, persistence
boundaries, current verification evidence, and remaining gaps.

## Quick Start

### Prerequisites

- Docker & Docker Compose (recommended), **or**
- Python **3.11** (verified dependency-lock baseline), Node.js **22.13+ in the 22.x series** (CI uses Node 22), Neo4j 5.18+, Ollama. Other declared Node ranges are in `package.json`; broader Python support remains unverified.

### Option A: Docker (easiest)

```bash
git clone https://github.com/alinojoumi8/crowdlens.git crowdlens
cd crowdlens
cp .env.example .env

# Generate a password, then paste it into NEO4J_PASSWORD= in .env
openssl rand -hex 24

# For local Ollama in Docker, set these two values in .env:
# LLM_BASE_URL=http://ollama:11434/v1
# OPENAI_API_BASE_URL=http://ollama:11434/v1
# For MiniMax M3, use the hosted configuration below instead.

# Start all services in CPU-compatible mode
docker compose up -d

# Pull the required models into Ollama
docker compose exec ollama ollama pull qwen2.5:32b
docker compose exec ollama ollama pull nomic-embed-text
```

Open `http://localhost:3000` — that's it.

All published ports bind to loopback. To opt into NVIDIA GPU acceleration,
start the same stack with the GPU override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Option B: Manual

**1. Start Neo4j**

```bash
docker run -d --name neo4j \
  -p 127.0.0.1:7474:7474 -p 127.0.0.1:7687:7687 \
  -e NEO4J_AUTH=neo4j/replace-with-a-unique-password \
  neo4j:5.18-community
```

**2. Start Ollama & pull models**

```bash
ollama serve &
ollama pull qwen2.5:32b      # LLM (or qwen2.5:14b for less VRAM)
ollama pull nomic-embed-text  # Embeddings (768d)
```

**3. Configure & run backend**

```bash
cp .env.example .env
# Set NEO4J_PASSWORD and edit endpoints if services use non-default ports

cd backend
uv sync --frozen --dev
uv run python run.py
```

**4. Run frontend**

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`.

## Configuration

All settings are in `.env` (copy from `.env.example`):

```bash
# LLM — points to local Ollama (OpenAI-compatible API)
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL_NAME=qwen2.5:32b

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<unique-local-password>

# Embeddings
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_DIMENSIONS=768

# External market lookups are disabled unless explicitly enabled
MARKET_DATA_PROVIDER=none
```

OpenAI-compatible providers use the chat-completions transport. The backend and
OASIS also support MiniMax through the Anthropic Messages adapter.

### MiniMax M3

To use M3 for generation and simulation, set these values in `.env`:

```dotenv
LLM_DEFAULT_PROVIDER=minimax
LLM_API_KEY=your-minimax-api-key
LLM_BASE_URL=https://api.minimax.io/anthropic
LLM_MODEL_NAME=MiniMax-M3
LLM_TRANSPORT=anthropic_messages
```

Both `LLMClient` and the OASIS/CAMEL adapter read `LLM_MODEL_NAME`.
`MINIMAX_MODEL` alone is not read by these paths. If you keep legacy
`OPENAI_API_KEY` and `OPENAI_API_BASE_URL` aliases, match them to `LLM_API_KEY`
and `LLM_BASE_URL`. Compose respects the selected LLM endpoint; Neo4j and
Ollama embeddings still use container service names. With M3, pull only the
embedding model in the Docker quick start.

Restart the manual backend after editing `.env`. For Docker, recreate the app
with `docker compose up -d --force-recreate`; an image rebuild
is needed only when application code changes. Check `GET /api/status` for
`data.llm.model == "MiniMax-M3"`. Saved simulations that explicitly specify an
LLM model (including economy configuration) should be re-prepared before a new
run; the switch does not rewrite old simulation artifacts.

See MiniMax's [Anthropic API documentation](https://platform.minimax.io/docs/api-reference/text-anthropic-api)
for the supported M3 model ID and endpoint.

Embeddings default to local Ollama. To benchmark Gemini, set `EMBEDDING_PROVIDER=gemini`, `GEMINI_API_KEY`, and `GEMINI_EMBEDDING_MODEL=gemini-embedding-2`; rebuild or re-embed graphs before searching with a different embedding provider.

Runtime readiness is exposed at `GET /api/status`. It reports Neo4j, embedding,
SQLite control-plane, migration, and simulation-restart status. The lightweight
container liveness endpoint is `GET /health`.

Project, case, task, and simulation metadata is stored transactionally in
the SQLite database under `backend/uploads/`. New background tasks retain
worker/attempt ownership; expired attempts fail honestly and require manual retry.
Existing JSON metadata is imported once without
being deleted; uploaded documents and generated artifacts remain on disk. See
[`docs/control-plane-migration.md`](docs/control-plane-migration.md) for backup,
migration, and recovery details.

Root report generation assigns one `request_key` per logical browser request.
Network retries reuse its task/report identity while the task record is retained;
a new manual invocation receives a new key. Generation also requires an explicit
workflow authorization in the browser, backed by the SQLite control database.
Choose the provider/model, frozen inputs, maximum physical requests and runtime
before upload. The aggregate allowance includes graph/profile workers, simulation
children, memory updates, report/proposal work and actual transport retries.
Refresh and manual retries retain consumed requests.

The workflow bar displays usage, remaining requests and effective terminal reason.
**Stop** closes admission and preserves partial output; an already submitted
request may still incur provider billing. Interrupted reports stop polling and
require explicit recovery with new authorization. Request/time controls do not
enforce a dollar ceiling. See [the execution contract](docs/workflow-execution.md)
for API use, supported providers and recovery semantics.

Run the embedding benchmark from `backend/`:

```bash
uv run python scripts/benchmark_embeddings.py --providers ollama gemini --graph-id <graph_id>
```

## Architecture

CrowdLens uses an abstraction layer between the application and the graph database:

```
┌─────────────────────────────────────────┐
│              Flask API                   │
│ graph.py simulation.py diagnostics.py   │
│ report.py market.py status.py           │
└──────────────┬──────────────────────────┘
               │ app.extensions['neo4j_storage']
┌──────────────▼──────────────────────────┐
│           Service Layer                  │
│ ControlPlane  SimulationRunner           │
│ GraphBuilder  GraphTools  ReportAgent    │
└──────────────┬──────────────────────────┘
               │ storage: GraphStorage
┌──────────────▼──────────────────────────┐
│         GraphStorage (abstract)          │
│              │                            │
│    ┌─────────▼─────────┐                │
│    │   Neo4jStorage     │                │
│    │  ┌───────────────┐ │                │
│    │  │ EmbeddingService│ ← Ollama       │
│    │  │ NERExtractor   │ ← Ollama LLM   │
│    │  │ SearchService  │ ← Hybrid search │
│    │  └───────────────┘ │                │
│    └───────────────────┘                │
└─────────────────────────────────────────┘
       │ graph/search          │ workflow metadata
┌──────▼──────┐         ┌─────▼──────────────┐
│ Neo4j 5.18 │         │ SQLite control DB  │
└─────────────┘         └────────────────────┘
```

**Key design decisions:**

- `GraphStorage` is an abstract interface — swap Neo4j for any other graph DB by implementing one class
- Flask `app.extensions` provides runtime dependencies; existing manager singletons remain process-local and coordinate durable task ownership through SQLite
- SQLite WAL transactions for restart-safe project, case, task, and run metadata
- Uploaded files and large generated artifacts remain on the filesystem
- Hybrid search: 0.7 × vector similarity + 0.3 × BM25 keyword search
- Synchronous NER/RE extraction via local LLM (replaces Zep's async episodes)
- All original dataclasses and LLM tools (InsightForge, Panorama, Agent Interviews) preserved

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 16 GB | 32 GB |
| VRAM (GPU) | 10 GB (14b model) | 24 GB (32b model) |
| Disk | 20 GB | 50 GB |
| CPU | 4 cores | 8+ cores |

CPU-only mode works but is significantly slower for LLM inference. For lighter setups, use `qwen2.5:14b` or `qwen2.5:7b`.

## Development checks

```bash
UV_PYTHON=3.11 npm test # backend + frontend unit/component suites
npm run build     # production frontend bundle
UV_PYTHON=3.11 npm run check # tests + build
npm audit --audit-level=moderate
npm audit --prefix frontend --audit-level=moderate
```

Pull requests also run backend tests, frontend unit/component tests, the
frontend build, root and frontend dependency audits, Compose validation, and a
Docker image build. Unit/component checks and synthetic report checks do not
establish a complete live-provider pipeline or independently measured report quality.

The [2026-10-03 report reliability audit](docs/audits/2026-10-03-report-reliability.md)
records a fresh visible MiniMax-M3 upload → graph → four personas → two OASIS
rounds → root report → source proposal → accepted revision → reload/history reopen
on frozen application candidate `7f4d68e`. Original reports and failed attempts
remain preserved. **563 backend and 63 frontend tests plus build pass.** One
fictional journey verifies that boundary; independent claim/omission quality,
cross-packet reliability and exact-candidate release/deployment checks remain open.
The retained report includes a Round 1 contradiction that its mechanical score
missed; the saved revision remains Needs review. The [semantic-review follow-up](docs/audits/2026-10-03-semantic-review.md) checks explicit action counts and trace author/round/origin assertions, carries unresolved proposal findings into new revisions, and displays a read-only current assessment on retained reports. These limited checks do not certify truth or completeness. Independent held-out quality evaluation is next.
The [previous live tests](docs/audits/2026-10-03-live-cedarbrook.md) retain their
separate mixed-candidate and blocked outcomes.

## Use Cases

- **Communication planning** — explore possible responses to a draft announcement.
- **Market scenario exploration** — examine simulated reactions to financial news.
- **Policy scenario exploration** — compare possible responses to a policy proposal.
- **Research and storytelling** — study agent interactions under different assumptions.

## Documentation

- [Report reliability tasks and fresh actual-provider acceptance](docs/audits/2026-10-03-report-reliability.md)
- [Completed corrective task checklist](docs/tasks/2026-10-03-report-reliability.md)

- [Control/recovery repairs and exact-candidate synthetic verification](docs/audits/2026-10-03-control-recovery.md)
- [Previous fictional live-run request accounting](docs/audits/2026-10-03-bike-lane-request-accounting.md)
- [Real MiniMax browser tests, saved revision, blocked drafts and remaining gaps](docs/audits/2026-10-03-live-cedarbrook.md)
- [Visible-browser acceptance plan and execution status](docs/visible-browser-acceptance.md)
- [Workflow request/time authorization and Stop contract](docs/workflow-execution.md)
- [Product capabilities, contracts, and verification gaps](docs/product-capabilities.md)
- [ECC workflow and adoption plan](docs/ECC-WORKFLOW-PLAN.md)
- [Local ECC execution handoff and exact-candidate verification](docs/audits/2026-10-02-ecc-milestones-3-5.md)
- [Synthetic evidence evaluations and pending human review](docs/evaluations/evidence-quality.md)
- [Browser QA, screenshots, and test substitutions](docs/audits/2026-10-02-milestone4-browser-qa.md)
- [Local release verification and operational gaps](docs/audits/2026-10-02-milestone5-release-verification.md)
- [Evidence-first report proposals and revisions](docs/evidence-first-reports.md)
- [Architecture](docs/architecture.md)
- [Storage migration, backup, and recovery](docs/control-plane-migration.md)
- [Economic twin scenarios](docs/economic-twin-v1.md)
- [Jev evaluation and promotion boundaries](docs/jev-evaluation.md)
- [Roadmap](ROADMAP.md)
- [CrowdLens brand and rebrand plan](docs/rebranding.md)
- [Historical migration progress](docs/progress.md)

## License

AGPL-3.0. See [LICENSE](./LICENSE).

## Credits & Attribution

CrowdLens is a modified fork of the original work by [666ghj](https://github.com/666ghj), incorporating the local-runtime fork maintained by [nikmcfly](https://github.com/nikmcfly), originally supported by [Shanda Group](https://www.shanda.com/). The simulation engine is powered by [OASIS](https://github.com/camel-ai/oasis) from the CAMEL-AI team.

**Modifications in this fork:**
- Backend migrated from Zep Cloud to local Neo4j CE + Ollama
- Entire frontend translated from Chinese to English (20 files, 1,000+ strings)
- All Zep references replaced with Neo4j across the UI
- Rebranded the product to CrowdLens, with updated UI, visual assets, and documentation
- Preserved original author and contributor attribution and existing runtime identifiers
