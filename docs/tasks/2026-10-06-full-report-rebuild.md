# Whole-report rebuild — 2026-10-06

## Scope and execution

The user explicitly authorized rebuilding the whole report, resolving the prior selected-section summary scope decision. Used the existing visible browser's Report tools and recovery → Legal mode action to force regeneration with strict anti-repetition. This creates a separate root report; it does not accept earlier blocked section proposals or overwrite their parent.

Original: `report_8a7c03665e67`. New candidate: `report_05be40b9910c`. Browser remains on the new candidate at port 18810. Existing source scope, graph and completed simulation were reused; no new simulation was launched. MiniMax-M3.1-Flash-Preview used the user's existing provider/input authorization. The workflow allowance was renewed for the existing 30-minute duration and 1500-request ceiling.

## Verified result

- Persisted new report and progress both have status `needs_review`.
- All five sections contain fresh content: factual record/procedural posture, each side's arguments, contradictions/evidence gaps, settlement/procedural risk, and simulation/frozen forecast.
- The whole-report summary differs from the original. It labels the scenario low-confidence and says the incomplete record cannot support a confident merits prediction.
- Original report exactly equals the earlier frozen parent snapshot after regeneration.
- Source grounding, graph and simulation links match the original. Frozen forecast fields are unchanged except for evidence references, which were refreshed for this candidate.
- Workflow totals increased from 147 to 177 admitted requests (30 for this rebuild), with zero in flight at completion.
- Browser completion status was verified and the candidate left open. Private source contents, reports and raw provider outputs remain outside tracked receipts.

No application code changed in this milestone; runtime persistence and browser completion were verified directly. No factual ratings, exhaustive citation audit or human review time were measured. `needs_review` is not factual certification, and previous negative proposal audits were not converted into approvals.

## Next step

Audit this complete new candidate's source citations, motion-relief/service/docket statements, and summary against the original record. Distinguish evidence missing from the supplied record from material present but omitted in the report. Preserve unsupported findings and uncertainty. Then prepare the complete integration PR and verify CI on its actual candidate before merging; this milestone did not push, create a PR, or merge main.
