# Evidence-only reports and activity accounting

An explicit `evidence_only: true` choice bypasses forecast synthesis even when a
simulation has successful model actions. It persists through report storage,
resume, regeneration and immutable revisions. Request identities and existing
report lookup distinguish this choice. Legacy serialized reports and retry
fingerprints retain their existing shape. Numeric probability tables in fresh
evidence-only prose are blocked; source numbers remain attributed facts.

The simulation page provides an opt-in checkbox. Report tools can generate a
separate evidence-only report with interviews disabled. Existing report behavior
is retained by default. The report and simulation UI distinguish successful
written model responses, other actions, no-ops and failures. Scheduled posts and
scheduled-event metadata are separate records of planned input. Logged entries
are not deduplicated; unique posts and model actions are. Lifecycle markers do
not count as activity.

Validation: 827 backend tests, 12 Node tests, 71 Vue component tests and the
production build pass. Regression coverage includes persistence/rebinding,
request-key conflicts, legacy seal compatibility, cached report separation,
decimal probability tables, UI payloads and mixed-origin activity accounting.

A live browser test used an existing 24-round simulation with 8 successful
model actions: 6 written responses and 2 reactions. The completed four-section
report and downloaded Markdown contain no outcome percentages or probability
summary. Activity accounting displays 3 initial posts, 7 scheduled posts and
7 scheduled-event records separately from the 8 model actions (25 log entries).
All 405 prior report files were preserved byte-for-byte. The test used 22
additional admitted MiniMax requests; its workflow was stopped with zero in
flight. Private documents, generated reports and detailed receipts stay local.

Saved status remains `needs_review`, with the existing narrow procedural-source
warning. These checks verify the reporting contract, not factual certification,
legal accuracy, forecast calibration or measured human review quality.
