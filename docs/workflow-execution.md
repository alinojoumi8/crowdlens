# Workflow execution controls

This contract was written before the control/recovery implementation. It applies
to one explicitly authorized workflow, from ontology through graph extraction,
profiles/configuration, simulation (including graph memory and interviews),
report generation, and proposal drafting. Reading, accepting, rejecting, or
reopening an existing immutable revision does not authorize generation.

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
