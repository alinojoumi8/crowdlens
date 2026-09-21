# Source tracing and pilot comparison

Implemented scoped original-chunk retrieval and an expandable claim/source review panel. The new `evidence-v3` checks retain original excerpt text, document/page/chunk identifiers, hashes, per-source judgments, and precheck failures. Mixed support and contradiction is labeled `conflicting`. Unlinked claims remain unverified; model-omitted prose is retained as an additional review passage. Report prose is not silently rewritten or deleted.

Retrieval uses local BM25-style scoring over at most 2,000 original chunks / 8 million characters, strictly scoped to graph, case, and case version. Truncation is flagged. Four candidate chunks per claim are evaluated; candidates are not certified citations. Low confidence and failed calls remain unverified. The report cache includes the source-pool digest. Exact quote mismatches remain flagged, including possible layout/OCR differences; no normalization has been used to conceal those failures.

The model programming pattern follows TypeSafe's [citation-check guidance](https://docs.typesafe.ai/cookbooks/citation_check): local provenance checks, followed by typed source-support judgments. The confidence threshold remains provisional, and all features remain shadow-only.

## Same-report pilot

Saved report: `report_jev_traced_20260921` at `/report/report_jev_traced_20260921`. Original report and prose preserved. Scanned the same 340 original source chunks; no retrieval-size limit reached. Recheck took 33.19 seconds.

| Fixed 69 claims | Previous checks | New checks |
| --- | ---: | ---: |
| Claims with assigned/candidate source IDs | 53 | 69 |
| Supported | 12 | 2 |
| Contradicted | 1 | 1 |
| Conflicting | 0 | 2 |
| Unverified | 56 | 64 |

The old associations and new candidate-search judgments use different aggregation policies. This is evidence of increased trace visibility, **not evidence of increased semantic accuracy**. The new conservative checks require successful, confident judgments across retrieved candidates before accepting unopposed support. Additional candidates can expose ambiguity, conflicts, and retrieval noise. Labels have not been independently adjudicated.

An additional 52 previously unextracted passages are visible: 2 supported and 50 unverified. Across all 121 checks, unverified reasons are 98 insufficient/uncertain, 14 quote absent, and 2 missing source. The report remains `needs_review` by an explicit manual audit annotation; shadow inference does not change production report gating or prose.

Private metrics and full review data are in ignored `backend/uploads/evaluations/jev-real-case/tracing-run.json` and `traced-report.json`. `trace-pilot.py` preserves the fixed-claim comparison separately from added passage coverage. It makes paid provider calls and writes a new pilot report.

## Validation

244 backend tests, 11 frontend unit tests, 4 frontend component tests, and production build passed before deployment. Browser verification expanded a section, a claim, and its original excerpts with document/episode hashes. HTML in source excerpts is escaped. MiniMax remains primary and Jev remains in shadow mode.

Next quality work: independently review relevance/support labels, improve source candidate precision, and resolve quotation/attribution failures before treating the report as verified. No unsupported claim has been silently changed into a fact.

The report summary now has its own persisted, expandable checks as well. The frozen pilot summary was evaluated separately and is unverified; this brings the displayed total to 122 checks without changing the fixed 69-claim comparison or the 52 additional body passages. Summary results are recorded in `summary-tracing.json`.
