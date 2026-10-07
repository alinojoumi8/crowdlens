# Claim and quotation recovery

Completed the approved follow-up to complete-PDF-page retrieval. Private source text, party names, and source-file paths remain outside this receipt and Git. The original report, uploaded PDF, graph, simulation, and retained failed proposals were preserved.

## Implementation

- Added exact source-quote projection for unique whitespace-only variants. Every non-whitespace character must match the cited source window. Case, punctuation, Unicode spelling, OCR substitutions, dates, numbers, and negation are never corrected. Ambiguous matches and invalid scope/hash/window inputs remain unresolved and face the existing ledger gates.
- Projection preserves the model quote separately, materializes exact original text, and records source offsets under the digest-bound extract provenance. It does not change the claim's asserted wording or certify its meaning.
- A genuine absent quotation can trigger one substantive ledger correction, separate from the existing syntax correction. The model receives the original eligible windows and explicit findings; prior output remains untrusted and retained in private diagnostics. All requests consume the same workflow/deadline budget. Corrected output passes the same reserved-ID, source, scope, conditional, ledger, paragraph coverage, summary, and source-first audit gates. A repeated mismatch stops before drafting.
- New proposals use `evidence-draft-v10-exact-quote-recovery`; digest and revision validation recognize the policy and retain legacy support. No existing retained record was rewritten.

Regression tests cover unique exact offsets, substantive/date/negation/case changes, ambiguous repeated matches, one bounded correction with the normal downstream audit, and repeated mismatch blocking. Final `UV_PYTHON=3.11 npm run check`: 713 backend tests, 12 Node tests, 61 component tests, production build, and whitespace check passed.

## Retained failure replay

Replayed `proposal_75d230785cf84915beea72beaba8ec6d` without provider calls or modifying its artifact. Three of its four literal `quote_absent` findings were whitespace-only differences and now resolve to the exact source. One quote remains absent after whitespace normalization and still blocks. This refines the earlier literal-mismatch diagnosis: not all four were substantive source mismatches.

## Live browser verification

The prior app processes had stopped. Restarted frontend/backend on 18810/18811, reconnected to the operator's report, and manually renewed its expired allowance for 30 minutes under the existing MiniMax authorization, preserving the 1,500 total-request ceiling. Renewal did not automatically retry generation.

Browser New proposal created `proposal_e8e156dfa3ac4bbcbef046898050a209` for section one of `report_8a7c03665e67`, using MiniMax-M3.1-Flash-Preview. Three actual requests were retained: initial planning, one substantive planning correction, and drafting. The 30-claim ledger passed the deterministic claim/quote gates after correction. The draft contained only 11 paragraphs and omitted 19 planned claims, so the coverage gate returned 19 `undrafted_claim` findings. Saving remained disabled and the semantic audit was never called. Passing quotation linkage does not establish factual accuracy or successful end-to-end revision generation.

Browser Keep original confirmed Original retained; the proposal is now rejected, with its failure findings preserved. No child revision was accepted or published. Final allowance: 135 admitted requests total, zero in flight. Status-only screenshot: `/tmp/crowdlens-quote-recovery-retained.png`. The original report remains Needs review.

## Next step

Implement complete claim-to-paragraph rendering so every planned ordinary claim and server-owned exact extract is represented once, with provenance and the original model output preserved. Then run the source-first audit and a fresh visible proposal test. Independent factual review, exhaustive document coverage, and accepted-revision behavior on this private PDF remain unverified.
