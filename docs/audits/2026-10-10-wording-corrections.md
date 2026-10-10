# Bounded wording correction verification

## Change

Added explicit single-occurrence wording corrections alongside the existing
numeric/date path. Both retain original source snapshots, full before/after
section comparisons, immutable revision history and Needs review status. New
wording proposals seal the correction and source audit under policy
`focused-wording-correction-v2`; numeric proposals retain their existing policy.

## Validation

- 820 backend tests, 12 Node tests, 68 Vue tests, and production build passed.
- Synthetic cases cover page/date confusion and separate remote-oath locations,
  source dump bounds, multiple referents, blocked audit outcomes, preservation of
  parents and unselected sections, and patch digest tampering. Model outcomes in
  unit tests are synthetic; these tests verify control boundaries, not accuracy.
- Visible browser checks corrected four identified wording issues through
  separate source-reviewed revisions; originals retain their baseline hashes.
- A separate 24-round realistic single-seed run completed with four prepared
  participants, memory and economy off: 8 successful model actions, comprising
  6 written posts/comments and 2 likes, across three participants including both
  labelled sides. Initial and scheduled inputs were excluded from these counts.
- The provider allowance was stopped with zero requests in flight.
- After a backend restart, a transient polling warning persisted despite
  recovery. Polling errors now clear on successful status reads, while failed
  action errors remain visible. A component regression covers both cases.

## Limits

The private legal source packet and generated reports stay outside Git. The
model source audits are fallible, not independent human review. The saved report
remains Needs review; unselected content and forecasts remain inherited. The
longer simulation establishes that model interactions ran, not that they predict
a court outcome or represent the named parties’ actual views. No new report was
generated from that longer run in this milestone.
