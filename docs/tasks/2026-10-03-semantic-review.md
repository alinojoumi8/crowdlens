# CrowdLens semantic review milestone

Owner: coordinating implementation agent. Independent read-only AI code review:
control_recovery_review. Dependencies: retained actual artifacts and stopped
workflow; no additional provider inference required.

Authorized next step after the completed report-reliability tasks. Work remains
on the local integration branch. Existing reports, accepted revisions, source
packets, private diagnostics and main-checkout overlays remain unchanged.

- [x] Freeze the retained Round 1 contradiction and unverified-premise evidence;
  add fail-first regressions and distinct positive/negative trace examples.
- [x] Check explicit round/count/author/origin assertions against saved actions,
  disclose incomplete coverage, and require review on contradictions.
- [x] Carry unresolved proposal findings into new immutable revisions and expose
  current read-only review findings for retained reports without rewriting them.
- [x] Verify review status, evidence and safe rendering in tests and the visible
  browser; run the full check and reconcile documentation/evidence.

Scope: deterministic trace contradictions and retained proposal-audit findings.
No new model judgment is treated as an independent label. Arbitrary paraphrase
entailment, omissions, calibration and measured human reviewer effort still need
held-out packets with authentic independent review. This milestone makes no
release/CI/deployment claim or automatic prose correction.

Completed locally on application candidate `4faf90a`, with 658 passing tests and
visible retained-artifact browser verification. See [the audit](../audits/2026-10-03-semantic-review.md).
Next: independently reviewed held-out source/claim/omission evaluation.
