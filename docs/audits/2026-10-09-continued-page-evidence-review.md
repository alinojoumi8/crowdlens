# Continued-page evidence and review navigation

## Change

Source retrieval now includes complete immediate neighboring PDF pages when the combined excerpt fits the existing 4,000-character extract limit. A contiguous range can be used by the server's exact-extract contract, preserving page-spanning conditions and negation. Source locators expose the first and last page. This does not guarantee semantic completeness across arbitrary pages, chunk boundaries, or oversized pages; existing bounded-context limitations remain visible.

Evidence review now shows a short claim preview, retains the full claim on expansion, and links each claim directly to its displayed sources. Excerpts are keyboard focusable and page ranges are displayed. Acceptance gates and original-report preservation are unchanged.

## Verification

- Regression: a conditional offer on page 1 includes its payment condition and non-admission on page 2, excluding unrelated oversized page 3.
- Component regression: preview shortening preserves the complete claim, source links resolve to the source article, page ranges render, and excerpts remain focusable.
- Local check: backend tests, Node tests, Vue component tests, and production build.
- Visible browser check on the existing fictional Cedarbridge proposal: expanded full claim, followed Read Source 1, observed the source destination. At widths 375, 768, and 1440 the document did not overflow horizontally. This was a focused layout check, not a full accessibility certification or performance benchmark.

## Live MiniMax probe

Runner: `backend/scripts/verify_multidocument_drafts.py --live --model MiniMax-M3.1-Flash-Preview --suite continued-pages --output-dir <new-local-directory>`.

Final local artifacts: `/tmp/crowdlens-multidoc-20261009-pages-v3/`. Fixture SHA-256 and provider usage are recorded in result.json. Final run admitted six model requests within its 30-request / 15-minute allowance.

| Fictional case | Result | Observed behavior |
| --- | --- | --- |
| continued_offer | ready, saved separate Needs review revision | Preserved $900 payment condition, no admission, and no acceptance |
| continued_negation | ready, saved separate Needs review revision | Preserved NOT endorsed, hypothetical support, testing condition, and absence of testing |
| oversized_conditional | blocked | conditional_excerpt_unavailable; zero model calls and no accepted child |

Parent hashes remained unchanged; the runner checks child state, unselected section preservation, and idempotent acceptance. Initial v1 and v2 runs used a generic negation-case query and returned no_original_evidence with no model calls for that case. The final fixture uses a subject-specific inspector/repair/testing query so it exercises page continuation. This is a development probe, not a frozen or blinded evaluation. Earlier runs used three requests each, bringing this milestone's live probe total to twelve requests.

These tests use fictional page-marked stored text and the real draft/audit/revision services, with isolated fixture storage. They do not exercise physical PDF upload/extraction, graph construction, simulation, or browser-triggered generation. The browser results page is a side-by-side rendering of actual service outputs; the app browser check uses a previously saved fictional proposal. No new private legal documents were transmitted. Human quality labels and measured human review time remain null.

## Next verification gap

Run a physical multi-page PDF through upload, extraction, graph storage and evidence drafting, including a condition that crosses a stored chunk boundary. Verify original PDF page locators and retained source text end to end. Keep oversized or incomplete evidence blocked rather than increasing the extract cap without evidence.
