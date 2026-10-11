# Next CrowdLens delivery sequence

Authorized in the project chat on 2026-10-11. This continues the completed
[previous sequence](2026-10-10-delivery-sequence.md) from deployed `898bb25`.
T-numbers are planning references in the
[Confluence backlog](https://alinojoumi8.atlassian.net/wiki/spaces/CROWDLENS/pages/590020),
not verified Jira issue keys.

## 1. Spending controls and roadmap reconciliation (T10)

- [x] Define an explicit USD admission policy with frozen operator pricing,
  integer reservations before transport and durable estimates/unknown usage.
- [x] Cover concurrency across processes, transport retries, restarts, late
  responses, overruns, explicit renewal and idempotency with offline tests.
- [x] Expose initial/renewed terms and persisted spending summaries in the UI.
- [x] Reconcile stale deployment, readiness and coordinated-backup roadmap items.
- [x] Verify browser authorization, upload/project binding, blocked-budget reload,
  retained estimates/reservations and explicit renewal at 375/768/1440px.
- [x] Finish exact-candidate CI and integration: PR #21 merged at `61a65f1`;
  candidate and main CI passed all three jobs. Deployment follows the batch.

Request/time controls remain supported without pricing. The spending policy
limits admission using the selected assumptions, not provider invoices or M Plan
quota. No model price is inferred and no live generation is authorized by this
implementation. Local checks pass 916 backend and 95 frontend tests plus the
production build. See [the contract](../workflow-execution.md) and
[browser evidence](../audits/2026-10-11-spending.md).

## 2. Current workflow verification (T06)

- [x] Refresh offline PDF/text upload through review/export evidence against
  the candidate, identifying every substituted/seeded stage.
- [x] Prepare the fictional Cedarbrook hosted canary: 60 requests, 30 minutes,
  four agents and two rounds on the existing MiniMax M Plan.
- [ ] Obtain the pending explicit allowance before hosted execution. No response
  to the question has been received; no hosted calls were made.

PR #22 merged at `66af7dd021563ed0f1b85e2430f2e14e59c144e6` after all three
candidate CI jobs passed. Offline evidence is in [the workflow audit](../audits/2026-10-11-workflow-and-human-handoff.md).
Generation, graph storage, preparation and simulation are scripted substitutes,
so this does not close the hosted workflow acceptance criterion.

## 3. Human quality baseline (T08)

- [x] Verify existing blinded packet preparation and import/scoring on frozen
  sources; prepare a concrete reviewer handoff. Four historical actual-model
  packets, eight original documents and 19 claims have blank human forms. The
  importer returns PENDING with zero human rows and null metrics. These packets
  do not measure the current MiniMax preview model.
- [ ] Import actual independent human ratings when supplied. Never substitute
  model labels or synthetic checks for human quality measurements.

## 4. Recovery and retention (T07/T09)

- [x] Exercise corrupt optional memory and Neo4j outages with preserved outputs;
  quarantine/atomic writes and stable graph-memory retry IDs implemented.
- [x] Verify scoped deletion preserves unrelated cases, graphs and artifacts;
  reject unsafe project paths before mutation and retain metadata on disk errors.
  See [the contract](../recovery-retention.md) and
  [rehearsal evidence](../audits/2026-10-11-recovery-retention.md).
- [ ] Finish candidate CI, integration and one final preserved-data deployment.
