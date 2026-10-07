# Workflow execution controls

This contract was written before the control/recovery implementation. It applies
to one explicitly authorized workflow, from ontology through graph extraction,
profiles/configuration, simulation (including graph memory and interviews),
report generation, and proposal drafting. Reading, accepting, rejecting, or
reopening an existing immutable revision does not authorize generation.

Implemented and synthetically verified at `34ad6d2` on 2026-10-03. The
[audit](audits/2026-10-03-control-recovery.md) records exact identity, failing
before regressions, final checks and real-provider limits. Monetary admission
and a fresh complete live workflow remain unverified or future scope.

- The operator confirms a provider endpoint identity, model, input description,
  maximum physical generation requests, and wall-time allowance. A fresh workflow
  needs an explicit authorization operation before generation. Existing artifacts
  need an explicit attachment to an authorization; opening them never creates one.
- One durable SQLite ledger is shared by API workers, graph/profile threads,
  simulation children, report workers, and proposal workers. Admission is an
  atomic write transaction immediately before each transport attempt. SDK retries
  are disabled; supported transports implement visible, counted retries.
- Failed attempts, timeouts, uncertain delivery, and retries consume requests.
  Reservations are never refunded. Missing token usage remains unknown. Measured
  token categories are retained separately; they are not billing amounts.
- The clock begins with the first admitted request. Its persisted deadline covers
  all stages and pauses, including retries and child processes. Refresh, repeated
  clicks, worker replacement, and application restart cannot reset either limit.
- Stop closes admission for the entire workflow before stopping owned work.
  An in-flight request can finish, time out, or have an unknown outcome. Local
  termination does not guarantee cancellation or reversal of provider billing.
  Partial files and activity logs remain. Late responses record usage but cannot
  schedule follow-on work or publish successful artifacts after Stop.
- Exhaustion closes admission. Completion of a final admitted request may record
  its result, but cannot schedule another request. Time expiry and Stop reject late
  publication. Existing task leases and artifact publication fences still apply.
- Recovery is an explicit operation with a new total ceiling and deadline
  authorization. The previous count, attempts, authorizations, and usage remain.
  It is never performed by polling, refresh, or automatic retries. A workflow
  with uncertain in-flight attempts requires operator acknowledgement.
  A reauthorized deadline starts at that explicit operation; it is not granted
  by a later first call. Imported legacy consumption is included in the ceiling;
  retain its historical receipts separately because a count import does not
  reconstruct individual attempts or their token usage.
- Primary-provider generation is supported. A different boost provider/model or
  unmetered external generation path is rejected within this authorization.
  Embeddings must use the configured local, non-billable provider; remote
  embeddings require a separate supported accounting design. This contract does
  not claim a monetary ceiling or a forecast-quality guarantee.

Expected states are `authorized`, `stopped`, `request_limit`, and `runtime_limit`.
The status includes admitted, finished, in-flight/unknown attempts, elapsed time,
remaining requests, terminal reason, and usage by stage. Report interruption is
terminal for polling and retains partial sections. Manual recovery creates a new
worker attempt under the existing ownership and immutable-revision rules.

## Operator and API use

The Home and case-version flows require explicit input/provider/request/runtime
confirmation before generation. A hash binds exact uploaded filenames/bytes,
the requirement and URL list; a late authorization response for changed input
cannot enable it. The global workflow controls rehydrate existing bindings and
show the effective provider/model, consumption, deadline and Stop state.
Scenario pages display supported effective settings; reopening never prepares
or starts a simulation automatically.

| Operation | Contract |
| --- | --- |
| `GET /api/execution/configuration` | Non-secret configured provider/model and whether durable controls exist; no generation probe or authorization. |
| `POST /api/execution/authorize` | Explicit confirmed terms, unique `request_key`, input description/fingerprint, configured provider/model, `max_requests`, `max_seconds`; fresh consumption zero. Validate local embedding/secondary-provider restrictions before admission. |
| Legacy attachment through `/authorize` | Explicit existing `project:ID`, `simulation:ID`, `report:ID` resources and `consumed_requests`; verify resources before recording authorization. Retain original receipts and scope. Never attach by merely opening an artifact. |
| `GET /api/execution/resolve?resource=report:ID` | Resolve an existing binding without creating/rebinding one. |
| `GET /api/execution/WORKFLOW_ID` | Read counters, stage usage, elapsed time, remaining allowance and terminal reason; expiry can reconcile matching owned work, never authorize replacement generation. |
| `POST /api/execution/WORKFLOW_ID/stop` | Close admission before cancelling matching owned work; preserve partial artifacts/receipts and truthful in-flight uncertainty. |
| `POST /api/execution/WORKFLOW_ID/reauthorize` | New confirmed total ceiling above consumed requests, runtime, unique `request_key`, and `acknowledge_unknown: true` when unfinished attempts exist. Retain history and supersede the old epoch. Idempotent replay preserves the current authorization. |

Generation requests carry `X-Workflow-ID` or an explicit `workflow_id` and must
agree with existing resource bindings. Missing authorization returns a structured
428; exhausted/stopped/conflicting workflow admission returns 409; invalid terms
return 400. Unexpected application errors retain their error behavior. These
controls are designed for the local single operator and do not add authentication
or tenant isolation.

Supported creation responses bind new project, simulation, root-report and
unbound accepted-revision resources. GET, resume and regeneration responses do
not rebind related existing graph/simulation/report IDs. Root/proposal request
idempotency stays separate from physical transport accounting: returning an
existing request identity grants no extra provider allowance.

For a paid test, use the [visible acceptance plan](visible-browser-acceptance.md)
and obtain new approval before submitting an authorization operation. The old
fictional bike-lane allowance is exhausted. No recovery or new spending is
implied by the prepared input packet or a visible synthetic preview.
