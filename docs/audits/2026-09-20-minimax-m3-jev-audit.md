# MiniMax M3 migration and Jev suitability audit

Date: 2026-09-20. Baseline commit: `7598986`.

## Recommendation

Use **MiniMax M3 for generation** and introduce **Jev as an optional decision service**. Start with interview participant selection, followed by retrieval reranking. Add claim/source checks after preserving source provenance. Evaluate stance analysis and bounded economic actions separately before allowing either to change simulation behavior.

Jev is not a replacement for the app's whole LLM client. It selects, scores, and judges supplied options; it does not write personas, posts, reports, explanations, or new search queries. That distinction follows TypeSafe's [System One model](https://docs.typesafe.ai/concepts/system-one.md).

The implementation plan is [here](../superpowers/plans/2026-09-20-jev-decision-services.md). No Jev production feature is enabled by this audit.

## Scope and evidence

Reviewed the backend generation, graph extraction/storage/search, simulation preparation/runtime, reporting, forecast, economy, provider adapter, deployment configuration, and existing tests. Used the codebase MCP graph first, refreshed a stale index, then read current source. `backend/scripts` is excluded from the graph and was inspected directly. This is an architectural and AI workload audit, not a comprehensive security review or simulation-validity study.

Read live TypeSafe docs through HTTPS; the web reader failed for that site, but direct Markdown downloads succeeded. A synthetic Jev request was sent using the existing local credential. Uploaded documents, case records, and actual agent data were not included in that probe.

## M3 changes implemented

- Local ignored `.env`: `LLM_MODEL_NAME` and `MINIMAX_MODEL` changed from `MiniMax-M2.7` to `MiniMax-M3`; credentials retained. The application reads `LLM_*`, not the named `MINIMAX_MODEL` alias.
- Kept `https://api.minimax.io/anthropic`. MiniMax documents M3 on this transport; its thinking output is off by default on this endpoint. See [official MiniMax API reference](https://platform.minimax.io/docs/api-reference/text-anthropic-api).
- `docker-compose.yml`: selected LLM endpoint now reaches both app and OASIS instead of being replaced by the hard-coded Ollama URL. Local Docker users must set `LLM_BASE_URL=http://ollama:11434/v1`; the README and example explain this.
- `OasisProfileGenerator._generate_profile_with_llm` and `SimulationConfigGenerator._call_llm_with_retry`: replaced direct OpenAI SDK calls with the existing transport-aware `LLMClient`. Existing repair/retry behavior and credential-free template profiles remain. Generation requests now have an explicit 8,192-token output cap; exceptionally large responses may require smaller batches or a future configurable cap.
- Added preparation regressions for M3, fenced JSON, and truncated JSON; extended existing adapter tests to cover M3 and M2.7.
- Repository defaults still support an offline Ollama installation. This machine's configured primary model is M3. Existing saved simulation artifacts are not rewritten.

## Workload map

Paths are relative to the repository; symbol names identify the implementation even if line numbers move.

| Functionality and source | Current behavior | Jev fit | Recommendation |
|---|---|---|---|
| Interview selection: `backend/app/services/graph_tools.py:1359`, `_select_agents_for_interview` | One LLM JSON call chooses indices plus prose reasoning; failure chooses the first profiles | **Direct replacement.** A relevance Score per supplied profile, with deterministic unique selection and diversity | First pilot. Preserve the `(agents, indices, reasoning)` return contract; build the explanation in code |
| Retrieval: `backend/app/storage/search_service.py:67`, `search_edges`, `search_nodes`, `_merge_results` | Vector/fulltext candidates, normalized 0.7/0.3 blend | **Quality addition.** Score query/candidate relevance after retrieval | Second pilot. Keep Neo4j and embeddings; bound shortlist, preserve original order on failure, never invent facts |
| Report checking: `backend/app/services/report_agent.py`, `validate_report_output`, `evaluate_report_quality`, `extract_evidence_cards` | Regex/keyword checks, penalty score, heuristic evidence cards | **Quality addition.** Choice: supports / contradicts / insufficient evidence, evaluated against a source span | Add provenance first. A generated graph fact cannot verify itself |
| Stance: `backend/app/services/stance.py:74`, `infer_stance` | Relation names plus positive/negative word presence | **Heuristic replacement.** Choice for target-specific stance, with unknown separate from neutral | Shadow evaluation first; preserve graph direction, speaker, target, and time in state |
| Diagnostics: `backend/app/services/simulation_runner.py:1463`, `_infer_stance` | Party-name keywords choose a favorable side | **Heuristic replacement.** Choice for the speaker's endorsed position | Strong semantic fit. Do not infer a favorable position merely from a party mention |
| Sentiment: `backend/app/services/forecasting.py:453`, `_text_sentiment` | Counts positive/negative terms | **Heuristic replacement.** Score using concrete target-specific positive/negative descriptions, plus Noul for whether the target is addressed | Evaluate as a measurement change. Cache once per action and reuse; do not call Jev on every diagnostics GET |
| Economic decisions: `backend/app/services/economy.py:1217`, `_default_decisions` | Batched LLM returns action + free-form payload for each selected agent | **Partial replacement.** Choice among complete, legal candidate intents supplied by code | Later experiment. Existing job selection can be bounded; writing a new job description still needs M3 or a template |
| Graph entity alignment: `backend/app/storage/neo4j_storage.py:925`, `_write_extractions_batch` | Lowercased name forms merge identity within a graph | **Decision addition.** Judge candidate alias/entity pairs from existing attributes and source evidence | Propose links for review; no autonomous destructive merge. Exact same names may already have lost identity distinctions |
| NER: `backend/app/storage/ner_extractor.py:76`, `extract`, `extract_batch` | Generates new entities, attributes, relation facts from text | **Not a full replacement.** Select among code-detected date/amount/name spans; classify fixed ontology types; verify proposed relations | Keep M3 extraction. A Jev option list cannot contain a source value the candidate finder missed |
| Ontology: `backend/app/services/ontology_generator.py`, `generate` | Generates entity/relation schema | **Not a full replacement.** Could select a known template if a curated catalog is introduced | Keep M3 for open-ended ontology generation |
| Personas and setup: `backend/app/services/oasis_profile_generator.py`, `backend/app/services/simulation_config_generator.py` | Generates persona prose, schedules, seed events, and parameters | **Partial fit only.** Known role/stance labels can be decisions; prose and novel events need generation | Keep M3; retain deterministic setup rules and explicit user choices |
| Query decomposition and report tools: `graph_tools.py:959`, `_generate_sub_queries`; `report_agent.py`, `_generate_section_react`, `chat` | Creates new query strings, chooses tools, synthesizes answers | **Partial fit.** Route among known tools with complete known arguments; choose from query templates | Keep M3 when a new query or explanation is required. Existing no-expansion retrieval already avoids an LLM call |
| Forecast-mode inference: `backend/app/services/forecasting.py:79`, `infer_forecast_mode` | Legal/market keyword counts; explicit normalized settings elsewhere | **Optional semantic fallback.** Choice: legal_case / market_economy / general / unclear | Low priority. Explicit settings win; do not add latency where existing rules suffice |
| Embeddings, ledger, persistence, IPC, polling, forecast arithmetic | Deterministic vectors/storage/transitions/math | **No replacement** | Keep in code. Jev confidence is not a probability that a legal or market outcome will occur |

## Findings that affect implementation

### F1 — High: preparation bypassed the provider transport; fixed

The two preparation generators called `OpenAI(...).chat.completions.create` against the configured Anthropic endpoint. Mocked transport-boundary regressions reproduced template fallback for personas and failure for configuration. Both now call `LLMClient.chat`. The tests exercise the resulting generated content and outgoing `/v1/messages` payload.

### F2 — High: retrieval drops provenance needed for citation checking; open

`Neo4jStorage._write_extractions_batch` records episode document/version/page/paragraph metadata. `GraphToolsService.search_graph` at line 415 constructs a smaller edge dictionary containing UUID, fact, relationship name, and endpoint IDs. `ReportManager.extract_evidence_cards` then reconstructs cards from rendered strings. These cards lack a dependable raw-source locator.

Before semantic citation checking, carry graph/case version, document ID, episode ID, source locator, exact excerpt, and an observed-versus-simulated origin through retrieval and report evidence. Test that version and graph boundaries survive every conversion. Keep existing exact arithmetic and evidence rules; semantic agreement alone must never promote a missing-source claim to verified.

### F3 — High: current stance rules misclassify negation and party mentions; open

`SimulationRunner._infer_stance('The plaintiff has not established its case. The motion should fail.')` matches `plaintiff` first and produces `plaintiff_favorable`. The intended position in that synthetic statement is defendant-favorable. Keyword counting also misses sarcasm, quotations, changing targets, and mixed positions. Jev is a plausible replacement, but evaluate these cases on labeled examples before changing simulation or forecast signals.

### F4 — Medium: extraction cache does not distinguish models or prompts; open

`backend/app/storage/extraction_cache.py:89` keys cached output by cache version, file, chunk, and ontology only. Changing M2.7 to M3 can legitimately reuse prior extraction results, so a rebuild is not proof that every chunk used M3. Include provider/model and extraction-prompt version in future cache metadata and keys. Benchmark with isolated cache directories; do not delete existing cached user data as part of an experiment.

### F5 — High before advanced tool workflows: OASIS history translation is lossy; open

`backend/scripts/llm_provider_adapter.py`, `_convert_messages`, converts content to plain text and maps non-assistant roles to user. It does not preserve structured assistant `tool_calls` or tool-result IDs. `_to_chat_completion` translates outgoing tool-use blocks but drops thinking blocks. A single-turn M3 tool-call smoke passed; a complete multi-turn CAMEL/OASIS rollout was not validated by that test.

Add a dedicated round-trip regression before replacing OASIS action selection or enabling interleaved thinking: assistant tool call → matching tool result → final answer, including tool-only assistant messages. This is a provider-adapter task, not a Jev capability. M3's default thinking-off behavior avoids one issue, but does not restore lost tool IDs.

### F6 — Medium: candidate coverage and workload size limit the economics pilot; open

`EconomyRuntime._build_decision_contexts` limits open jobs to 25 and counterparties to a nearby slice. Jev can only choose supplied options. Unsupported choices must yield `do_nothing`, a declared M3 escalation, or an omitted/rejected intent according to the policy; they cannot be converted into fabricated IDs or amounts. Revalidate against current state inside `EconomyStore.execute_intent`, retaining idempotency and ledger invariants.

### F7 — Setup: credential spelling needs normalization before using the SDK

The local configuration has `TYPESAFE_API-KEY`; the official SDK expects `TYPESAFE_API_KEY`. The audit probe read the existing value explicitly in memory. Rename/migrate the setting when implementing the gateway; do not expose it in the frontend or logs. No key value is included in the audit or probe artifact.

## Proposed design constraints

- Backend-only decision gateway, separate from `LLMClient`; modes `off`, `shadow`, `on` independently per feature. Defaults remain `off`.
- Pin the evaluated model, initially `jev-1.13.0`, and record the actual response model, question version, state hash, candidate IDs, latency, token usage, and fallback reason. Re-evaluate before changing the model pin.
- One narrow judgment per question. Batch independent questions over the same state. A dependent question needs a new request only when its evidence or candidate options depend on a prior answer.
- Use comparable Scores for graded relevance, Choice for mutually exclusive classes or complete intent IDs, and Noul for independent yes/no conditions. A Noul near 0.5 is uncertainty, not medium sentiment.
- On timeout, invalid schema, invalid IDs, unavailable credentials, budget overflow, or service error, retain the baseline behavior. Claim checks record `unverified` rather than treating service failure as a pass.
- Cache by exact state, question definitions, model, graph/case version, and relevant policy version. Cache judged facts once; changing display weights should not trigger inference.
- Bound input and question budgets. Current docs specify 64k total request tokens and 32k for state plus longest question; do not substitute character counts for exact token guarantees. Start with small shortlists, reject/split over-budget inputs, and measure actual `usage`. See [models](https://docs.typesafe.ai/models.md).
- Confidence is distribution concentration, not source reliability, business authorization, or forecast accuracy. Thresholds must be fitted to held-out task data. See [confidence](https://docs.typesafe.ai/confidence.md).

## Validation and expected benefit

**Observed:** 165 backend tests passed after the transport fix; 11 frontend unit tests and 2 component tests passed; the production frontend build passed. Live M3 returned the requested JSON through `LLMClient`; the OASIS adapter returned a typed `record_result` tool call with `status=ok`.

**Deployment verified:** rebuilt the Docker image and recreated only the app service. `GET /api/status` reports `healthy=true`, provider `minimax`, model `MiniMax-M3`, healthy Neo4j/embeddings, and usable vector search. The new container also passed a live M3 JSON request and resolved the OASIS model to M3. Live simulation-configuration generation passed separately. No complete multi-agent simulation or end-to-end report was rerun; the open tool-history finding above still applies.

**Observed Jev probe:** [`2026-09-20-jev-probe.json`](2026-09-20-jev-probe.json) records one synthetic request, five questions, model `jev-1.13.0`, 868 input tokens, 151 output tokens, and 0.383 seconds elapsed. The explicit deadline passage scored 2.0/2, hearing-date passage 0.27/2, and irrelevant passage 0/2. It labeled source support and the negated plaintiff statement as expected. These are connectivity examples, not an accuracy, latency, or cost benchmark.

**Expected, not measured:** interview selection may remove a generative JSON call; a bounded economic-action pilot could remove a portion of per-tick generation. Retrieval and citation checking add inference and cost; their value is evidence quality, not automatic cost reduction. Stance replacement adds inference to what is currently cheap deterministic code.

Collect baseline M3 request counts, token usage, p50/p95 latency, fallback rate, and end-to-end task time before claiming savings. Compare both systems on the same versioned fixtures and shortlist. Keep labeled development and held-out sets separate, split by source/case to avoid leakage, and include long inputs, contradiction, no-match, irrelevant party mentions, multilingual text, and service failures.

## Source guide

- [TypeSafe HTTP API](https://docs.typesafe.ai/api.md): current endpoint and answer schema; direct HTTP or the Python SDK can implement the gateway.
- [Python SDK](https://docs.typesafe.ai/sdk/python.md): package `typesafe-sdk`, import `typesafe_sdk`, canonical credential name.
- [Score](https://docs.typesafe.ai/primitives/score.md), [Choice](https://docs.typesafe.ai/primitives/choice.md), [Noul](https://docs.typesafe.ai/primitives/noul.md): judgment design and interpretation.
- [Reranking cookbook](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md): shortlist first, then judge query/candidate pairs; its benchmark numbers are not forecasts for this repository.
- [Citation cookbook](https://docs.typesafe.ai/cookbooks/citation_check.md): verify quote presence in code, then judge its contextual support.
- [Entity alignment](https://docs.typesafe.ai/cookbooks/entity_alignment.md), [function calling](https://docs.typesafe.ai/cookbooks/function_calling.md), [source-value selection](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md): bounded candidate designs for later experiments.
