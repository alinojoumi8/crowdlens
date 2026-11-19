# Setup and configuration

The [README quick start](../README.md#quick-start) covers the Docker path.
This page covers the manual install, configuration, architecture, hardware,
and development checks.

## Prerequisites

- Docker & Docker Compose (recommended), **or**
- Python **3.11** (verified dependency-lock baseline), Node.js **22.13+ in the 22.x series** (CI uses Node 22), Neo4j 5.18+, Ollama. Other declared Node ranges are in `package.json`; broader Python support remains unverified.

## Manual setup

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

### Scanned PDF evidence

PDF extraction preserves page markers. Image pages with little native text use local Tesseract OCR (`tesseract` with English language data on the backend host). If OCR is unavailable or fails, ingestion reports the affected page rather than silently discarding scanned evidence. OCR text can contain recognition errors; check quotations against the original PDF during report review.

Source-backed proposals can select a complete marked PDF page within a larger stored graph chunk. Page windows retain the original chunk hash, exact offsets, and PDF page number. Eligible conditional material is copied verbatim by the server; oversized or incomplete page windows remain blocked. Retrieval discloses when fragment matches are omitted or adjacent pages may contain continued attribution or conditions. A complete extracted page does not establish complete context, exhaustive document coverage, or factual accuracy; compare adjacent original pages before accepting a revision.

Quotation recovery maps a unique whitespace-only variant back to exact source text and records the original offsets. It never changes wording, punctuation, case, dates, numbers, or negation. A genuine quotation mismatch permits one counted ledger correction within the workflow budget; repeated mismatches remain blocked. Corrected claims still require the normal coverage and source-first audit checks before a proposal can be saved.

### Authorization fails before a website or PDF upload

Workflow authorization currently covers the configured primary AI provider and local Ollama embeddings. Optional Jev modes must be off for this workflow. If the UI reports that optional Jev provider modes are enabled, restart the backend with:

```bash
JEV_INTERVIEW_MODE=off JEV_RERANK_MODE=off JEV_EVIDENCE_MODE=off uv run python run.py
```

Run this from `backend/` with the usual application environment loaded. These process overrides preserve `.env` settings for separate Jev evaluations. The UI checks configuration before authorization and displays the server's error reason when a request fails. After restarting, refresh the page and authorize your selected sources again.

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
container liveness endpoint is `GET /health`. The home page shows [storage and model metadata readiness](readiness.md); status polling never generates text or embeddings. A listed model is not an inference test.

Project, case, task, and simulation metadata is stored transactionally in
the SQLite database under `backend/uploads/`. New background tasks retain
worker/attempt ownership; expired attempts fail honestly and require manual retry.
Existing JSON metadata is imported once without
being deleted; uploaded documents and generated artifacts remain on disk. See
[`docs/control-plane-migration.md`](control-plane-migration.md) for backup,
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
enforce a dollar ceiling. See [the execution contract](workflow-execution.md)
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
