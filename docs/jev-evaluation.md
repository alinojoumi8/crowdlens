# Jev decisions: operation and evaluation

MiniMax M3 remains the text-generation and OASIS model. Jev (`jev-1.13.0`) supplies optional interview relevance scores, evidence relevance scores, and source-support judgments. This release implements plan tasks 1–5. Stance attribution and economic action selection remain separate experiments.

## Configuration

Set `TYPESAFE_API_KEY` in the server `.env`. The canonical name uses underscores, including before `KEY`. Never place it in a frontend variable. Restart the backend after editing configuration.

| Flag | `off` | `shadow` | `on` |
|---|---|---|---|
| `JEV_INTERVIEW_MODE` | Existing M3 selection | Record Jev proposal and M3 panel; return M3 | Apply eligible Jev panel, fall back to M3 |
| `JEV_RERANK_MODE` | Existing hybrid retrieval | Score a 30-item shortlist; return original results | Apply Jev ordering, retain source text and hybrid scores |
| `JEV_EVIDENCE_MODE` | Existing report behavior | Save associations and checks; preserve quality status | Unverified or contradicted critical source claims require review |

Repository defaults are `off`; the local rollout uses `shadow`. `on` is an explicit operator setting, not automatic promotion. All thresholds are provisional: interview eligibility score >=0.5/3; evidence confidence >=0.8. Review labels and freeze thresholds before enabling a feature. `/api/status` exposes the pin, policies, modes, and credential availability, without credentials or a remote health probe. Availability means configured, not proof the provider is currently reachable.

Rollback one feature by setting its flag to `off` and restarting the backend. Missing keys, timeouts, rate limits, malformed answers, oversized requests and concurrency saturation preserve baseline behavior or leave source claims unverified. Interactive requests have one attempt. The default timeout is 3 seconds; it is a transport timeout, not a total report deadline. Two in-flight requests per backend process is a stricter cap than two per simulation. Multiple worker processes each have their own cap.

Decision records are atomic JSON under `backend/uploads/simulations/<id>/decisions/`, or a hashed graph-scope directory under `backend/uploads/decisions/`. They contain scope, hashes, policy/model, numerical judgments, usage, latency and failure reasons; raw excerpts and credentials are excluded. A runner caches at most 512 successful validated responses. Cache identity includes full input, questions, graph/case/run scope, model and policy. Report metadata intentionally retains evidence excerpts and claims alongside other uploaded case data.

## What source checking establishes

Graph relations are extracted claims. Original episode text with document identity is evidence. Cards retain graph/case/version, document and episode IDs, excerpt hash, page/paragraph when available, and offsets explicitly relative to the stored chunk. Legacy episodes without document provenance remain unverified. A quote is checked for literal presence before semantic support is judged. Simulation dialogue never verifies a source fact.

M3 proposes explicit claim-to-evidence associations using exact substrings of the generated section and known IDs. Invented claim text is rejected; unknown source IDs remain unverified. No reliable associations means unverified coverage. This is an advisory check on extracted associations, not a guarantee that every report assertion was found or that the underlying document is true. Jev judges the source context, including negation, attribution and quantities. Existing deterministic numeric/ledger quality checks remain in place. Every cited source is judged separately; a confident contradiction wins. Changed section text, source cards, scope, model, mode or policy invalidates its saved checks.

## Reproducible commands

From the repository root:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/evaluate_jev.py \
  --feature evidence --input backend/tests/fixtures/jev/evidence.jsonl \
  --output backend/uploads/evaluations/evidence-replay.json

PYTHONPATH=backend backend/.venv/bin/python backend/scripts/evaluate_jev.py \
  --feature evidence --mode live --input backend/tests/fixtures/jev/evidence.jsonl \
  --output backend/uploads/evaluations/evidence-live.json
```

Use `interviews` or `reranking` with the corresponding JSONL file. Replay is the default and imports no provider client. Its fixture predictions are handcrafted metric regression examples, not observed model accuracy. Live explicitly calls Jev and an M3 typed-judgment comparator with the same inputs. The comparator is not the full production interview/report workflow; its latency must not be presented as end-to-end savings. Outputs may contain the supplied source data; keep case datasets in private uploads rather than git.

Each row has a `case_id`, `split`, `label_source`, literal `expected`, and a recorded `predicted` (or no prediction when skipped). Live rows also require `state`. Interview/ranking outputs use string candidate IDs; interview candidates use their zero-based request indices. Ranking rows include `shortlist_ids` and independently labeled `relevance` for the entire judged pool, including relevant items absent from the shortlist. Evidence uses a claim and an original provenance-bearing excerpt. `critical` distinguishes serious claim errors.

Metrics distinguish malformed, skipped and incorrect records. Reports include false-supported counts/rates, critical errors, review coverage, useful interview precision, profession diversity, candidate Recall@30, nDCG@10, requests, usage, fallback/cache rates, latency percentiles and optional recorded end-to-end report seconds. The accuracy interval resamples cases rather than correlated questions. Small fixture sets cannot provide meaningful deployment confidence. Request count and latency are measured in live mode; full report time must come from a real staged report run.

## Promotion gates

The committed fixtures are **synthetic and unreviewed**: 2 interview cases, 2 retrieval cases and 8 source cases. They cover no-match, negation, ambiguity, multilingual text, quotation context, hostile-looking source text, wrong versions, missing sources and missing retrieval candidates. They do not meet the planned domain benchmark sizes.

Build development and held-out sets split by case/source, with domain review: initially at least 50 interview scenarios, 100 retrieval queries and 200 claim/source pairs. Freeze question wording, thresholds and model pin on development cases; evaluate held-out cases once. Expand samples when uncertainty is too large. M3 agreement is not a ground-truth label.

- Interviews: useful-candidate precision within 2 percentage points of the existing selection baseline, with lower p95 selection latency; inspect role coverage and no-match behavior.
- Retrieval: measure candidate Recall@30 first, then require nDCG@10 improvement without meaningful recall regression. Global ANN graph filtering can omit relevant candidates; Jev cannot recover them.
- Evidence: zero false-supported critical held-out contradictions and <=1% false-supported overall, with review coverage and uncertainty reported. Test missing/old provenance and quote-context failures.

A five-question probe or the small fixtures must not turn any feature on. Evaluation output deliberately retains `promotion_ready: false`; promotion remains an explicit reviewed rollout decision.

## Local smoke results (2026-09-20)

The live evidence fixture run matched 8/8 labels: 6 Jev requests plus two deterministic source rejections, with no false-supported result in this small set. Jev p95 was about 487 ms. The interview run matched both synthetic panels (2/2). On retrieval, the fully covered case had nDCG@10=1; the deliberately omitted-source case had recall and nDCG=0. Their mean of 0.5 is a candidate-coverage test, not measured domain retrieval quality. Exact list-match accuracy is not a useful ranking metric.

A separate M3-association → Jev-verification → JSON-save/reload workflow persisted a `supported` shadow check and an atomic decision record, with report status still `completed` (about 1.1 seconds, synthetic source). Full multi-agent simulation and end-to-end generated-report quality were not benchmarked. Machine-readable smoke results are under `docs/audits/jev-*-live.json` and `jev-staging-summary.json`.
