# Conditional PDF context recovery

## Change

Recover complete PDF page windows from two or three consecutive original chunks in the same document, graph, case and version. Each boundary must have exactly one matching overlap of 64–1000 characters; reconstructed text is capped at 30,000 characters. Gaps, duplicate positions and ambiguous overlaps refuse reconstruction. Existing 4,000-character conditional-extract, packet and scope limits remain in force. Complete page boundaries do not establish semantic completeness across pages.

Reconstruction carries original component identifiers, indexes, text and SHA-256 hashes. The claim validator independently reconstructs the text; the review UI distinguishes the reconstructed hash from original component hashes and identifies joined-text offsets. Identical recovered page windows are deduplicated.

A planner may return no ordinary claims when it explicitly excludes irrelevant background and server-owned conditional claims remain. Combined-ledger validation, source coverage and the source-first audit still run.

## Verification

- `UV_PYTHON=3.11 npm run check`: 763 backend tests, 12 Node tests, 63 Vue tests and production build passed (838 tests total).
- Physical three-page fictional PDF generated with PyMuPDF, extracted with FileParser and split with the production splitter (1100 characters / 100 overlap). No individual original chunk contains the full conditional page. Retrieval reconstructs the complete page including its testing condition and final negation.
- Tests cover missing neighbours, wrong scope/document, duplicate positions, incorrect/short/repeated overlaps, altered reconstruction proof and component provenance rendering.
- Visible browser test at localhost:18816 used the production review component and proposal/revision API with isolated fixture storage and real MiniMax-M3.1-Flash-Preview. It is a focused revision test, not a new upload/graph/simulation run. Remote embeddings were skipped and disclosed.
- Final proposal `proposal_e2a5d57563f34bfdb1cab7bba51828ea` reached ready, then was saved through the browser as `report_c6d0564190b64590bc96bf5db200d3ec`. One exact conditional extract retained both “only if” and “No endorsement is given and no testing has been received”.
- Parent metadata, outline and full-report hashes remained unchanged. The other section remained identical. The child remains `needs_review`.
- Earlier browser attempts exposed rejection of a valid empty ordinary ledger and duplicate recovered pages; both were fixed before the successful final save.

Local evidence is in `/tmp/crowdlens-conditional-browser`: physical PDF, extracted sources, parent hashes, verification.json, backend logs and revision-saved.png. This temporary path is not a durable release artifact. No private legal document was used in this milestone.

No visual baseline was available: visual regression status is inconclusive. Accessibility conformance and Core Web Vitals were not measured. Model audit is not factual certification. Pages that cannot be recovered within these bounds still require a clearer source or manual review.
