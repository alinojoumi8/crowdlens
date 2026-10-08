# Fictional multi-document source verification — October 8, 2026

## Result

PR #5 was merged after backend, frontend and Docker CI succeeded. Main merge commit `e5645fd3620ecf56ff3f2b8df4139377943b092f` also passed CI.

Ran three newly authored fictional packets through the actual EvidenceDraftingService and MiniMax-M3.1-Flash-Preview. Each packet contains three original document windows. All three produced ready proposals and separate immutable Needs review revisions. Nine physical requests were admitted, zero remained in flight, within the explicit thirty-request/fifteen-minute test allowance. Parent artifact hashes and unselected sections remained unchanged. Acceptance retries returned the same child.

| Packet | Sources | Ledger claims | Model calls | Observed source comparison |
| --- | ---: | ---: | ---: | --- |
| Conditional offer | 3 | 6 | 3 | Preserved possible replacement if photographs are supplied versus replacement only after $700 payment; purchaser rejection and lack of settlement. |
| Conflicting quantity | 3 | 8 | 3 | Preserved original 40-carton entry, correction to 34, count-only witness scope, and disputed six missing cartons/nine defective components. Summary retained original count and correction. |
| Missing evidence | 3 | 3 | 3 | Kept no inspection separate from no defects; no recorded spending separate from no spending; possible support separate from endorsement; proposed $2,400 budget separate from approval or expenditure. |

These comparisons are the coordinating AI's inspection of actual source/output text, not human labels or an independent blinded benchmark. Human quality metrics and review time remain null. Three successful cases do not establish general factual accuracy or forecast calibration. Existing frozen development/holdout corpus files were not changed.

## Reproducible boundaries

Added `backend/scripts/verify_multidocument_drafts.py` and a fixed fictional fixture file. The CLI requires explicit `--live`, exact configured model, Jev evidence mode off, and a new direct `/tmp/crowdlens-multidoc-*` directory. It uses a separate durable WorkflowLedger and bounded proposal deadlines. No key or environment value is written to result artifacts. Do not invoke it without provider/input/spending authorization.

Example after authorized provider configuration:

```bash
UV_PYTHON=3.11 uv run python scripts/verify_multidocument_drafts.py \
  --live --model MiniMax-M3.1-Flash-Preview \
  --output-dir /tmp/crowdlens-multidoc-new-run
```

Sources are supplied by isolated fixture storage. This tests drafting, audit and revision services with the real model, not upload/PDF extraction, graph storage, simulation or browser-triggered generation. The earlier full application journey remains separate evidence.

Actual output: `/tmp/crowdlens-multidoc-20261008-v1/result.json`; raw proposal diagnostics and immutable reports are under its `reports/` directory. A local comparison page at `http://127.0.0.1:18814/` shows source windows next to observed section and summary text and was opened in the browser. It is a QA results page, not an application UI change.

The existing structural evaluator passed 195 checks in one repeat. Its fifteen frozen corpus cases yielded five ready and ten correctly blocked outcomes using deterministic substitutes, with zero real model calls. This structural result must not be combined with the three live cases as a model-quality success rate. Receipt: `/tmp/crowdlens-ecc-eval-20261008-multidoc/results.json`.

Application behavior and existing real-case reports are unchanged during this milestone. No new private court document was used.

## Next step

Expand testing to longer documents and adjacent-page conditions, then improve the application's claim/source comparison readability. Retain Needs review, fail-closed acceptance, immutable parents, and explicit provider limits.
