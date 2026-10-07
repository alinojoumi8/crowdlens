# Complete PDF page windows for evidence proposals

Implemented the approved follow-up to the private motion-record browser test. Application graph chunks, original uploads, reports, and simulation state are preserved. Private source content and names are excluded from this receipt and Git.

## Change

Previously, retrieval chose approximately 2,000 characters inside a 9,000-character chunk, while conditional-source materialization required the entire chunk inside a 4,000-character claim bound. Large mixed PDFs therefore blocked before model drafting.

Retrieval now recognizes sequential `[PDF page N]` boundaries and selects a complete extracted page of at most 4,000 characters. The next sequential page marker must be present; terminal fragments are not identified as complete pages. If a nonliteral lexical hit falls in a chunk fragment, complete pages are independently ranked by query overlap. Exact requested quotations retain their original windows, including quotes crossing page boundaries. Irrelevant pages are not invented as a fallback.

The parent chunk text/hash, scope, source ID, and exact offsets remain intact. The selected page number and offsets are exposed in its locator. Source-window, packet, candidate, and document coverage limits remain visible; additional limitations disclose reranked fragment matches and possible attribution/condition continuations on adjacent pages. Extraction-page completeness does not prove semantic completeness or exhaustive source coverage.

For eligible conditional sources, the server selects and renders the exact full page text, rather than allowing a model paraphrase or a punctuation-derived sentence. The ledger recomputes the permitted exact range from the original chunk and window. Incorrect wording, linkage, source scope, hashes, incomplete/oversized ranges, and unsupported quotations remain blocked. New proposals use `evidence-draft-v9-complete-pdf-pages`; proposal digests and revision acceptance bind extract provenance under that policy. Legacy policy versions remain supported.

README documents page windows and the need to inspect adjacent original pages. Regressions cover exact PDF page offsets, cross-page requested quotes, fragment reranking, verbatim server resolution, paraphrase rejection, and incomplete/oversized pages; existing conditional-fidelity, proposal API, and immutable-revision tests also pass.

Final `UV_PYTHON=3.11 npm run check`: 706 backend tests, 12 Node tests, 61 component tests, production build, and whitespace check passed.

## Visible actual-provider verification

Restarted the integration backend on 18811 and reloaded the existing report at frontend 18810. Used the browser New proposal action for section one of `report_8a7c03665e67`, with the existing operator authorization and MiniMax-M3.1-Flash-Preview. No source upload, graph build, or simulation rerun was performed.

New proposal: `proposal_75d230785cf84915beea72beaba8ec6d`. Retrieval retained 29 source windows; all 26 guarded source windows could be materialized as exact extracts. The prior `conditional_excerpt_unavailable` failure was resolved. One actual model request produced four ordinary claims alongside 26 server-owned exact extracts. The four ordinary claims supplied purported quotes absent from both their cited original chunks and selected windows. The deterministic gate returned four `quote_absent` findings and disabled saving. This is a retained model-quality failure, not an accepted revision or factual certification.

Browser Keep original produced Original retained; the proposal is now `rejected`. Its original `blocked` findings remain stored. The current parent report JSON exactly equals the proposal's frozen parent snapshot. No child revision was created or published. Final allowance observation: 132 admitted requests out of 1,500, zero in flight; this follow-up added one request. Status-only screenshot: `/tmp/crowdlens-pdf-pages-original-retained.png`.

## Next boundary

The bounded page-retrieval implementation is complete. Actual-model ordinary claim/quotation reliability remains unresolved on this PDF. Independent factual review against original and adjacent pages, accepted-revision behavior on this PDF, and exhaustive large-document coverage remain unverified. Do not infer legal accuracy or winner probabilities from passing software tests, a complete extraction page, or a report's automated score.
