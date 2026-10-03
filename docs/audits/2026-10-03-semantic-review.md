# CrowdLens limited semantic review — 2026-10-03

COMPLETE for the scoped [task checklist](../tasks/2026-10-03-semantic-review.md).
Application candidate: `4faf90a4b5a57b99397a47e413a27c2ca2ac3806` on
`codex/crowdlens-control-recovery`, following `a748a9e` from baseline `c30e8b2`.
Runtime source SHA-256: `a65ffe53cbd41035841857dca969682230f5c10df44247b28017a7baa2bd6897`.

## Behavior and evidence

The retained actual fictional MiniMax report states “Round 1 contains no model
actions.” Frozen action `twitter:trace:11` records Maya Chen's Round 1 model
response. Deterministic validation now reports `round_action_count_conflict`
and requires review even if an existing mechanical score is 100.
Explicit nearby trace author, round and origin assertions are also checked.
Ambiguous, incomplete, duplicate or missing provenance cannot prove absence.
Negated, quoted and hypothetical statements are excluded. The narrow supported
syntax is covered by [regressions](../../backend/tests/test_report_semantics.py).
The retained fixture SHA-256 is `0b4d271cafa97bb946019bc3c4800de53df7a79866a0cc686a779e19e1077d6e`.

New immutable revisions carry nonblocking unresolved proposal findings in their
sealed metadata and validation issues. Existing child
`report_3d12d343d6fa4c5d86998d8d88ea042a` has a retained
`premise_unverified` finding on `claim_08`. Current assessment reads its sealed
proposal provenance, checks the manifest hash, proposal identity and recomputed
proposal digest, and exposes `proposal_premise_unverified`. This is the original
model auditor's unresolved judgment, **not an independent truth label**.
Missing or invalid provenance is explicitly unverified. Up to 30 nonblocking
findings are displayed; full sealed provenance remains available.

Report GET and by-simulation GET include `current_review` without rewriting the
saved status, markdown, quality score or revision files. The UI separately labels
saved status and current assessment, shows the exact disputed passage and recorded
trace, and discloses coverage limits. Historical completion log events cannot
mark the current assessment Completed. The old score is labelled “Automated checks.”
No report prose, source packet, prompts, forecasts or acceptance guards were rewritten.

## Verification

- Fail-first retained regression: 9 failed / 10 passed before integration.
- Browser-discovered completion-log regression: 1 failed / 2 passed before repair.
- Final `UV_PYTHON=3.11 npm run check`: **592 backend + 12 Node + 54 component =
  658 tests pass**, production build passes. No paid provider used by these checks.
- Independent AI code review found negation, duplicate count, missing-author,
  boolean-round and blank-author failures. All reproduced, repaired and covered
  by regressions. This is AI code review, not human factual adjudication.
- Visible Codex browser, final candidate, `http://127.0.0.1:18784`: retained root
  and child inspection, coverage expansion, reload, parent navigation and child
  reopen. Root shows one count contradiction; child shows it plus unresolved
  `claim_08`. Saved statuses remain Completed and Needs Review respectively;
  current UI requires review. Screenshots and DOM snapshots are in the bundle.
- **99 protected original-file hashes unchanged**, both copied report directories
  byte-identical after GET/reload/navigation. Main checkout retains its five
  unrelated overlays and was not modified.
- Read-only copied-artifact wrapper rejects mutation requests (403); existing
  workflow admission rejects an unauthorised generation request (428). Both
  original and copied ledgers contain 26 requests; **0 new model requests**.

The browser runtime uses copies of actual retained artifacts, with stopped
workflow and mutation denial. It shares the existing local Neo4j service for
read-only graph readiness. This is a retained-artifact review test, **not a new
live generation or fresh E2E pass**. Private wrapper/credentials are not included
in repository evidence. The application and frontend identity, wrapper hash,
HTTP receipts, preservation counts, logs and screenshots are retained in
[the evidence bundle](evidence/2026-10-03-semantic-review/verification.json).

## Remaining verification and next milestone

PARTIAL for general semantic quality. Limited syntax checks do not measure
arbitrary paraphrase entailment, unsupported implications, omissions,
calibration, cross-packet reliability or reviewer effort. No independent human
labels or human timing were invented; no quality gain is inferred from passing
regressions or mechanical scores. The fixture is development regression data,
not a held-out quality evaluation packet.

Next: freeze separate held-out source/claim/omission packets, obtain authentic
independent review with disagreements and timing retained, and execute the
existing scoring/import procedure. Human labels remain pending until supplied.
Remote exact-candidate CI, deployment reconciliation, release approval, monetary
admission and retention contracts remain separate outstanding work. No push,
main merge, deployment, model download or publication occurred.
