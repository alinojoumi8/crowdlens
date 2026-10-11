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
- [ ] Finish exact-candidate CI and integration.

Request/time controls remain supported without pricing. The spending policy
limits admission using the selected assumptions, not provider invoices or M Plan
quota. No model price is inferred and no live generation is authorized by this
implementation. Local checks pass 916 backend and 95 frontend tests plus the
production build. See [the contract](../workflow-execution.md) and
[browser evidence](../audits/2026-10-11-spending.md).

## 2. Current workflow verification (T06)

- [ ] Refresh offline PDF/text upload through review/export evidence against
  the candidate, identifying every substituted/seeded stage.
- [ ] Prepare a concrete fictional hosted canary with explicit request/time
  allowance and account-appropriate cost/quota terms; obtain separate approval
  before new MiniMax calls.

## 3. Human quality baseline (T08)

- [ ] Verify existing blinded packet preparation and import/scoring on frozen
  sources; prepare a concrete reviewer handoff.
- [ ] Import actual independent human ratings when supplied. Never substitute
  model labels or synthetic checks for human quality measurements.

## 4. Recovery and retention (T07/T09)

- [ ] Exercise corrupt optional memory and Neo4j outages with preserved outputs.
- [ ] Verify scoped deletion preserves unrelated cases, graphs and artifacts;
  record ownership and retention boundaries.
