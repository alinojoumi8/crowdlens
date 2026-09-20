# Report provenance and no-action forecast correction

## Changes

Reports without recorded simulation actions now return `forecast.status = unavailable`, with no outcome probabilities or numeric estimate. An empty ensemble cannot bypass this condition. The drafting contract no longer requests probabilities for these reports. The viewer labels them Source Analysis Report and explains forecast unavailability. The availability notice is excluded from evidence-section quality scoring. Forecasts with recorded actions continue to produce structured estimates; this change does not establish their calibration.

Legal reports load bounded original page-one chunks from Neo4j, scoped by graph, case, and case version. Explicit English motion-record headings and relief phrases provide a conservative procedural anchor. Original text, document/page/episode IDs, and a source-text hash are retained in report metadata and provided during outline and section drafting. Covers establish procedural context, not the extent of the uploaded record; other content still requires retrieval.

A deterministic check detects a limited set of affirmative statements assigning the anchored relief to a different procedural role. Ambiguous, oversized, or unavailable cover anchors require review rather than guessing. Detected attribution conflicts and unsupported forecast formulations override a high heuristic quality score. These checks are separate from Jev shadow judgments; no Jev feature was promoted.

## Real-case regression

Generated a separate four-section report against the same pilot graph and simulation context, preserving the original report. Generation and checks took 139.77 seconds. The new report identifies the defendants as moving parties using the original cover, and has no generated outcome-probability table or numeric forecast. Applying the new attribution validator to the original draft detects its moving-party error; the new draft does not trigger that check.

Saved report: `report_jev_source_fix_20260920` at `/report/report_jev_source_fix_20260920`.

The report remains **needs review** following manual audit. Source checks returned 12 supported, 1 contradicted, and 56 unverified. The contradicted aggregate contains differing judgments against two excerpts; it is a review signal, not an independently established false statement. Broader assertions, quotation accuracy, and completeness were not certified. The report also overgeneralizes from limited retrieved material in places. Cover anchoring is not comprehensive claim/source verification.

Private artifacts remain ignored under `backend/uploads/evaluations/jev-real-case/`: `source-fix-report.py`, `source-fix-run.json`, `source-fix-report.json`, `source-fix-report.md`, `source-fix-validation.json`, and `validate-source-fix.py`. The generation script issues paid provider calls; the validation script makes a manual review annotation on this pilot report.

## Validation and limits

The final test suite passes 239 backend tests, 11 frontend unit tests, and 2 frontend component tests. Frontend build passes. Rebuilt/restarted the Docker application and checked the saved report and app status. MiniMax-M3 remains primary; all Jev features remain shadow.

New tests cover zero-action forecasts, empty ensembles, continued forecasts with actions, scope mismatches, ambiguous/oversized source covers, persistence, detected attribution conflicts, review status despite high scores, source percentages versus unsupported forecast claims, and report-only prompt guidance.

The recognizer deliberately supports only explicit English motion-record headings with a small set of relief verbs. It does not parse every legal document, resolve multiple motions, adjudicate facts, or detect every paraphrased contradiction. Other formats and ambiguous sources require review. More complete claim/source association and independently reviewed evaluation remain the next priorities.
