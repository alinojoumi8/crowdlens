# Physical PDF end-to-end verification

## Scope and result

A user-authorized private, 21-page legal pleading was uploaded through the visible browser into the running local app. The workflow proceeded through extraction, graph construction, participant setup, a bounded live simulation, five-section report generation, recovery, section regeneration, source-based proposal review, and Markdown download. MiniMax-M3.1-Flash-Preview was used. This verifies workflow operation, not legal correctness or predictive accuracy.

Private source files, party names, report text, raw provider logs, and screenshots are excluded from this change. Local receipt: `/tmp/crowdlens-pdf-e2e-receipt.json`. The receipt is temporary local evidence, not a portable fixture or committed release artifact.

## Source and runtime evidence

- Uploaded bytes matched the selected original PDF. All 21 sequential PDF page markers survived extraction.
- The per-document extracted text was 44,004 characters; the combined project wrapper was 44,094 characters. All 12 original graph-source chunks matched the document's configured 4,500-character / 100-character-overlap splitter output exactly.
- Fast graph scan produced 55 entities and 174 relations before generated simulation memory. Later graph counts include generated memory and are not extra original evidence.
- The simulation used eight configured participants, three hourly rounds, four active participants per round, both platforms, one run, seed 42, baseline intervention, practical memory, and standard legal report depth. Both platforms completed all three rounds.
- Activity accounting: 43 logged entries; 14 unique posts, including four initial and six scheduled posts; 25 model decisions; zero unknown origins. Two model decisions were DO_NOTHING, leaving 23 non-noop forecast actions. The header now names that denominator explicitly. The generated forecast section's claim of an unresolved count discrepancy is a model interpretation error; the stored counts reconcile without changing the forecast.
- Report generation initially stopped in section two. After the provider-envelope fix, browser-triggered resume completed sections two through five and preserved the first completed section's hash. A later deliberate browser rerun of section one corrected a party-role wording error. The abandoned proposal retains its earlier parent snapshot; it was not accepted.
- The browser download matched the saved complete report byte-for-byte before the deliberate section rerun. The report remains Needs review, with a procedural-source attribution warning. The historical case metadata was not migrated in place.
- The workflow admitted 84 requests within its 250-request / 60-minute allowance, with no requests in flight at the final observation.

## Fixes and regressions

1. **Document classification:** an explicit filename now precedes body references, and Notice of Action is recognized as a pleading before generic judgment language. Fictional tests cover filename/body classification and persisted reload. A separate isolated reimport of the actual PDF persisted as a pleading. Existing imported records remain historical evidence.
2. **Report startup:** an admitted, pending or processing report task returns HTTP 202 planning before its worker persists the outline. Unknown and terminal missing reports remain HTTP 404. The regression pauses dispatch to exercise this exact admission boundary.
3. **MiniMax native tools:** the report agent recognizes a closed native named-call envelope with JSON arguments. Existing tool-name allowlisting and bounded completion remain enforced. Nested arguments work; unknown, malformed, unclosed and unwrapped calls are rejected. Live resume executed the previously missed tool format.
4. **Physical PDF condition regression:** a fictional two-page PDF is physically generated, extracted, chunked and retrieved. The server-owned exact extract retains the offer, continued testing condition and negation together across the page/chunk boundary.

The private full-section evidence proposal blocked with `conditional_excerpt_unavailable` before provider drafting: some selected conditional fragments lacked a complete bounded extract. No child was accepted and no safeguard was relaxed. This is a safe refusal, not a successful private-document draft acceptance.

## Validation and limits

`UV_PYTHON=3.11 npm run check`: 754 backend tests, 12 Node tests and 62 Vue component tests passed; production build passed. Focused browser layout checks at widths 375, 768 and 1440 found no document-level horizontal overflow. The corrected action-count label was observed in the live report.

No visual baseline was available, so visual regression status is INCONCLUSIVE. A complete accessibility audit and measured Core Web Vitals were not run. Source page locators are available for recoverable complete pages; not every stored fragment has a precise page locator. Generated statements and percentages still require substantive review. No blinded quality labels or measured human review times were collected.

## Next step

Build a focused regression for draft retrieval on a long physical PDF where a relevant conditional fragment straddles stored chunks. Recover the complete neighboring original context within the existing size limit and fail closed when that cannot be done. Then repeat browser proposal creation and acceptance on the physical fixture. Add an opposing filing only as a separate case version, preserving attribution and the notice-only baseline.
