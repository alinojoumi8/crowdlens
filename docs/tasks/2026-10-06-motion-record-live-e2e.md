# Private motion-record live browser test

Operator-requested localhost test, using their selected 319-page motion-record PDF and the already-authorized MiniMax-M3.1-Flash-Preview provider. Private document text, names, local source path, and screenshots containing document content are excluded from this receipt and Git. The original PDF was not modified.

The integration frontend/backend were stopped and restarted on ports 18810/18811. The actual visible browser file chooser uploaded the original PDF. The question asked for opposing arguments, contradictions, page citations, and missing evidence, with allegations separated from findings. No court-winner prediction was certified.

## Settings and observed results

| Stage | Actual result |
| --- | --- |
| Extraction | 319 pages; 49 near-empty native-text pages, including 44 with images. Local Tesseract OCR recovered scanned-page text. Full extraction returned 418,798 characters and 319 page markers in 45.8 seconds. |
| Graph | Deep evidence preset, 9,000-character chunks, 200 overlap, batch 8, provider concurrency 4. All 49 chunks processed; 25 graph provider requests. Graph structural score 82, including 220 isolated entities out of 371; this is not factual quality evidence. |
| Scenario | Legal-case mode, full memory, 8 participants, profile parallelism 4, 12 simulated hours, 60-minute rounds, 2–4 effective active participants, both platforms, baseline scenario, one seed (42), realistic runtime, economic twin off. Standard-depth legal report. |
| Simulation | Both platforms completed 12/12 rounds in 1m4s. 35 model actions (20 public feed, 15 community), 28 unique posts, 10 initial entries, 6 scheduled entries, 61 total logged entries, no unknown-origin actions. Transport requests and generated actions remain distinct. |
| Report | `report_8a7c03665e67`, five saved sections, persisted `needs_review`, automated checks 90/100. Deductions: `report_provenance_limited` and `procedural_source_unavailable`. Source grounding retained six source records; this does not prove exhaustive factual review of all 319 pages. |
| Proposal review | Section-one proposal `proposal_c7a8c4c6da9f4b7399cd3e05d31bb32e` blocked with `conditional_excerpt_unavailable`. A conditional retrieved excerpt exceeds the existing 4,000-character exact-claim bound. Save remained disabled; browser Keep original confirmed Original retained. No child revision was accepted or published. |
| Interaction | Browser Step 5 opened and an actual provider-backed report-chat request returned an evidence-limitations response. |
| Persistence | Reopened the report in the same browser; all five sections and Needs review/90 score remained. Zero requests in flight at final observation. |

Workflow `wf_89ee8631f7914d4c9180c61fbb1ca7aa` used 131 admitted requests out of the operator-approved 1,500-request/240-minute allowance, including failed content attempts and recovery. Breakdown: ontology 1, graph 25, profiles 8, time/event/agent configuration 1 each, graph memory 8, simulation transport 38, report 47, report chat 1. All received HTTP responses; that transport state does not mean every answer was usable. No dollar spend was measured.

## Fixes and recovery

- `6ad47a5`: mixed PDFs previously silently omitted scanned evidence. Added local English Tesseract recovery for image-bearing pages with fewer than 20 native-text characters and explicit PDF page markers. Missing/failed OCR raises an actionable error. Added three fictional regression tests and documented the prerequisite in README.
- `604771b`: MiniMax returned only a thinking block with `stop_reason=end_turn`, despite low output usage. The report writer's existing empty-response handling did not catch the client's exception. Added a typed empty-answer exception and one counted continuation inside the existing iteration limit. Repeated empty answers still stop. Safe diagnostics contain structural response metadata, never private thinking. Added transport and bounded-writer regressions.
- Three initial/manual recovery attempts stopped in section three with empty answer text. After the fix, section three and four completed. Section five subsequently failed the existing completed-Final-Answer check; one explicit browser Resume completed it. Prior sections were retained throughout; no upload/graph/simulation rerun was needed.
- Backend restarts caused two transient browser HTTP 500 console errors and a retained allowance alert. Final report reopen cleared the alert; no persistent HTTP failure was observed on the fresh page. These historical errors are not omitted from the test result.

Final `UV_PYTHON=3.11 npm run check`: 700 backend tests, 12 Node tests, 61 component tests, production build and whitespace check passed. Private runtime artifacts remain untracked. Status-only screenshots: `/tmp/crowdlens-motion-simulation-completed.png` and `/tmp/crowdlens-motion-report-completed.png`.

## Remaining verification gaps

The large-source proposal limitation remains: bounded page/paragraph retrieval needs a separate design and regression milestone that preserves conditional context and attribution. The guard was not weakened to force an accepted proposal. This live test verifies navigation, persistence, accounting, and fail-closed review behavior; it does not prove accepted-revision behavior on this PDF, independent legal accuracy, exhaustive source coverage, calibrated forecasts, accessibility, cross-viewport visual quality, or release readiness. No human factual labels or measured human review time were collected.

Next priority: page-addressed source coverage and appropriately bounded complete conditional excerpts for large mixed PDFs, followed by a fresh visible proposal-review test and independent factual review against the original pages.
