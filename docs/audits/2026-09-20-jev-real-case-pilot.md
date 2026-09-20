# Jev real-case pilot — 2026-09-20

Decision: keep interview selection, retrieval reranking, and evidence checks in shadow mode. MiniMax-M3 remains the primary LLM. This completes the ordered provenance, report, and promotion evaluation; activation was conditional and its gates did not pass.

## 1. Source rebuild

Rebuilt an isolated case from an existing original 319-page PDF, retaining document SHA-256, physical page, extraction method, case version, and graph identity. OCR supplemented 98 pages; five low-text separator pages remain. Original project and graph were preserved. Extraction cache was disabled for this pilot to avoid reuse of older extraction results.

The new graph contains 340 episodes, all with document/page/version provenance, and 536 relations, all with document provenance. All 43 extraction batches succeeded in 269.91 seconds. Provenance presence does not establish extraction accuracy or complete OCR accuracy.

## 2. Real report and integration fixes

Generated a four-section report in 125.26 seconds against the rebuilt graph. This was a report-only pilot using 197 existing simulated profile snapshots, not a new simulation run or real-person interviews.

The report misattributed the moving parties, contradicted by the original cover page. Existing forecast synthesis also inserted probabilities without simulated actions. The heuristic quality score of 88 did not detect these material problems. The saved report is manually marked `needs_review`; shadow checks did not automatically change baseline prose or publication behavior.

Fixed two observed integration defects:

- Source-check batches now obey both pair-count and serialized byte budgets without truncating source text (`evidence-v2`). Rechecking the same saved claims took 3.62 seconds: 13 supported, 0 contradicted, 52 unverified out of 65. The remaining reasons were 13 insufficient/uncertain, 22 missing source, 9 quote not in claim, and 8 quote absent. Checks are advisory and did not identify every report error.
- Gateway probability validation now accepts the existing 1% rounding boundary despite binary floating-point noise. Regression tests cover sums of 0.99 and 1.01, while rejecting 0.98 and 1.02. The tolerance was not broadened to accept materially invalid distributions.

## 3. Promotion evaluation

| Feature | Observed result | Decision |
| --- | --- | --- |
| Interview selection | Seven literal source-identity questions on the same explicit 30-person diagnostic pool. After the validator fix: Jev 6/7 exact panels and 9/10 correct selections; M3 7/7 and 10/10. Mean end-to-end latency: Jev 498.58 ms, M3 1945.51 ms. | Keep shadow: missed one named plaintiff; full 197-person production pool exceeds the 30-candidate budget and falls back to M3. |
| Reranking | Four real 30-candidate shortlists. Manual top-five inspection found comparable counsel results, better named-plaintiff results, worse moving-party relevance, and a main-affiant coverage problem in both outputs. | Keep shadow: mixed qualitative results; no independently labeled nDCG benchmark. |
| Evidence | Twelve literal source checks matched all expected labels: 6 supported, 4 contradicted, 2 insufficient. Real report coverage remained 13/65 supported. | Keep advisory/shadow: tiny diagnostic set and incomplete claim-source association are insufficient for gating. |

Labels were assistant-reviewed against original pages, not independently adjudicated. These small diagnostics do not establish broad accuracy. Preserve both interview runs: before the fix Jev had two invalid responses and 4/7 exact panels; M3 had 6/7. M3 variability between runs also limits inference. No cherry-picked reruns were used to claim promotion readiness.

## Usage evidence

Provider-reported token counts were retained, not converted to an unverified dollar estimate. Cache-read tokens are recorded separately in the raw telemetry.

| Phase/provider | Calls | Input tokens | Output tokens |
| --- | ---: | ---: | ---: |
| Graph/M3 | 43 | 155481 | 93975 |
| Report/M3 | 29 | 77961 | 21502 |
| Report/Jev | 7 | 51164 | 3450 |
| Initial evaluation/M3 | 8 | 29926 | 1200 |
| Initial evaluation/Jev | 23 | 74340 | 6024 |
| Interview recheck/M3 | 7 | 12095 | 1030 |
| Interview recheck/Jev | 7 | 37824 | 3318 |

This table covers instrumented phases only. Source rechecks and separate response-contract diagnostics are excluded, so it is not a complete bill. Raw decision records retain additional usage.

## Artifacts and validation

Private source data, prompts, report copies, raw diagnostic responses, and metrics remain in ignored `backend/uploads/evaluations/jev-real-case/`. Key files: `extraction.json`, `build.json`, `report-run.json`, `interviews.json`, `interviews-after-validator-fix.json`, `full-population.json`, `source-checks.json`, `reranking.json`, and `requests.jsonl`. Reproduction scripts are stored alongside them; running them issues paid provider requests and may create additional data.

Saved report: `report_jev_real_case_20260920`, available at `/report/report_jev_real_case_20260920`, marked needs review. The original generated text is preserved for diagnosis.

Validation after fixes: 229 backend tests, 11 frontend unit tests, 2 frontend component tests passed; frontend build passed. Docker app rebuilt and restarted; `/api/status` confirmed healthy M3, embeddings, Neo4j, and all three Jev features in shadow mode.

## Next implementation priorities

1. Correct report party-role attribution and suppress unsupported forecast probabilities for report-only cases; evaluate against explicit source facts, not heuristic quality scores.
2. Support bounded full-population interview scoring without silently dropping candidates; remove diversity-driven displacement for literal identity questions, then evaluate on multiple cases.
3. Improve claim/source association and candidate retrieval coverage before expanding reranking or enabling evidence-based report gates.
4. Obtain independently reviewed labels and a larger held-out evaluation before any promotion.
