# Retrieved-source accounting — 2026-10-06

## Implemented

Proposal policy v12 accounts for each retrieved original window: it must be cited by the validated ledger or have a unique, bounded task-irrelevance reason. Exclusions cannot reference foreign or already-cited windows. Missing windows and quotation errors share the existing single counted planning correction; claim and paragraph ceilings are unchanged. Invalid ledgers fail before coverage checking. Remaining unaccounted windows block before prose generation.

Exclusions are retained in digest-protected extract provenance and sent to the source audit. That audit still checks material omissions against originals and may reject exclusions. Acceptance independently checks the accounting contract. Neither citation presence nor an exclusion reason establishes semantic completeness.

The audit may now use up to 90 seconds per request; other phases retain 60 seconds. Every call is bounded by the existing total proposal deadline and workflow admission. Automatic transport retries remain disabled. The scripted structural harness verifies the updated phase-specific timeout contract; frozen corpus inputs and expected judgments were not edited.

## Verification

- `UV_PYTHON=3.11 npm run check`: 730 backend, 12 Node and 61 component tests passed (803 total), plus production build. Whitespace check passed.
- Tests cover missing windows receiving exactly one correction, repeated gaps blocking before drafting, an adverse document audit rejecting an exclusion, invalid exclusion reasons/IDs/duplicates, and acceptance rechecking source accounting.
- Browser test on preserved report `report_8a7c03665e67`, using the previously authorized private PDF and MiniMax-M3.1-Flash-Preview. Workflow allowance was manually renewed for the existing 30-minute duration and 1500-request ceiling; neither provider nor input destination changed.
- First proposal `proposal_e61fcb50ad884b84ae553bb922671777` used four counted requests and failed during a 60-second audit timeout. It remains retained, with no factual judgment inferred from the timeout.
- Fresh retry `proposal_9a8e50a1cc8b4a56a73a9daf672c0608` used four counted requests: planning, correction, drafting, audit. All 29 admitted windows were accounted for: 28 cited, one excluded with an explicit reason. All 30 ledger claims were rendered in 30 paragraphs; 18 paragraphs were appended by the server.
- The AI audit returned supported for 30/30 claims and 30/30 paragraphs, but document material omission and summary inconsistency remained blocking. Its omission rationale changed from the prior exhibit-index/valuation material to requested motion relief and service/current-docket information. This is not evidence of complete coverage of the 319-page record, nor factual certification.
- Browser Keep original completed. The retry is rejected with diagnostics retained; the original report equals the frozen parent snapshot. Workflow totals: 147/1500 admitted requests, zero in flight. No revision accepted or published. Private text and raw diagnostic packets remain outside tracked documentation.

## Outstanding scope decision

The original summary is a whole-report forecast and has no literal mapping to the selected factual/procedural section. Existing `summary_edit_scope` explicitly preserves abstract summaries absent a trusted mapping. Rebuilding it would expand the correction to all report sections and their source support. A user question is pending: rebuild the whole-report summary, or preserve it and keep saving blocked for summary review. No broader rewrite was inferred from elapsed time.

Next: review the original opening motion/service material and identify which docket facts the record actually establishes, then handle the whole-report summary within the user's chosen scope. Do not invent unavailable procedural facts or weaken negative audit gates. Integration PR preparation remains appropriate; merging requires review and successful CI on the actual complete candidate, with unresolved workflow limitations explicitly assessed.

Scope resolved later on 2026-10-06: the user authorized a whole-report rebuild. The [new candidate receipt](2026-10-06-full-report-rebuild.md) records the separate regenerated report, refreshed summary, preserved original, and remaining source-review boundary.
