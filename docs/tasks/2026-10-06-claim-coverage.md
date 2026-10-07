# Complete claim rendering — 2026-10-06

## Implementation

Policy `evidence-draft-v11-complete-claim-coverage` appends missing ledger claims verbatim to a structurally valid draft. Each added paragraph retains exactly one claim ID and its kind. Citations resolve from the persisted ledger; allegation attribution, conditions and uncertainty are not paraphrased. Coverage resolutions record paragraph index, claim ID, ledger text and server origin in digest-protected extract provenance. Raw model responses remain retained separately.

Malformed drafts are not repaired. Adding paragraphs cannot exceed the existing 60-paragraph ceiling. Coverage checks remain active after rendering, and revision acceptance independently requires every ledger claim ID. All rendered claims and paragraphs still undergo the source-first AI audit; neither copying nor linkage certifies truth. Existing policies remain supported.

## Verification

- Final `UV_PYTHON=3.11 npm run check`: 719 backend, 12 Node and 61 component tests passed (792 total); production build passed. `git diff --check` passed.
- Regressions cover omitted claims reaching an adverse audit, invalid links/kinds, paragraph overflow, immutable input, and rejection of a digest-consistent incomplete candidate at acceptance.
- Read-only replay of retained proposal `proposal_e8e156dfa3ac4bbcbef046898050a209`: 19 omitted claims were appended, producing 30 paragraphs covering all 30 claims. Retained artifacts were not rewritten; replay is structural evidence only.
- Visible browser run on `report_8a7c03665e67` created fresh proposal `proposal_49573e9a3fbb45e798d2a8433f25c335` using MiniMax-M3.1-Flash-Preview. Four actual counted calls: planning, one planning correction, drafting and source audit. The workflow reached 139/1500 admitted requests with zero in flight.
- Fresh ledger contained 30 claims; model draft contained 12 paragraphs; 18 missing claims were appended. Final 30 paragraphs linked every planned claim. AI audit returned supported for 30/30 claims and 30/30 paragraphs, but reported one document material omission and an inconsistent retained summary. No summary edits were proposed. Saving stayed blocked; this is not factual certification.
- Browser Keep original completed; proposal is rejected with diagnostics retained. Persisted original report equals its frozen parent snapshot. No new revision was accepted or published. Private document contents and diagnostics remain outside tracked receipts.

## Next step and merging

Next address the source audit's material omission and retained-summary inconsistency using original sources, then repeat the visible proposal test. Do not weaken negative audit judgments or claim that full document coverage is established.

GitHub inventory: canonical `alinojoumi8/crowdlens` has no open PRs. Before this milestone commit, the integration branch was 91 commits ahead of freshly fetched `crowdlens/main`. Historical release checks do not validate this current candidate.

Start preparing an integration PR next. Merge to main after review of the complete current diff, successful CI on the actual PR candidate, and verification that remaining findings are correctly retained as explicit product limitations or resolved defects. A correctly blocked source proposal is expected safety behavior and does not by itself prohibit merging its infrastructure fix. Do not label the evidence workflow complete while these live omissions remain. This milestone does not push or merge the branch.
