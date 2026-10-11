# Workflow execution controls

This contract was written before the control/recovery implementation. It applies
to one explicitly authorized workflow, from ontology through graph extraction,
profiles/configuration, simulation (including graph memory and interviews),
report generation, and proposal drafting. Reading, accepting, rejecting, or
reopening an existing immutable revision does not authorize generation.

Implemented and synthetically verified at `34ad6d2` on 2026-10-03. The
[audit](audits/2026-10-03-control-recovery.md) records exact identity, failing
before regressions, final checks and real-provider limits. The optional USD
admission policy below was added on 2026-10-11; it does not establish a provider
invoice ceiling. A fresh complete hosted workflow remains separately gated.

- The operator confirms a provider endpoint identity, model, input description,
  maximum physical generation requests, and wall-time allowance. A fresh workflow
  needs an explicit authorization operation before generation. Existing artifacts
  need an explicit attachment to an authorization; opening them never creates one.
- One durable SQLite ledger is shared by API workers, graph/profile threads,
  simulation children, report workers, and proposal workers. Admission is an
  atomic write transaction immediately before each transport attempt. SDK retries
  are disabled; supported transports implement visible, counted retries.
- Failed attempts, timeouts, uncertain delivery, and retries consume requests.
  Physical request counts are never refunded. Missing token usage remains unknown. Measured
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

Expected states are `authorized`, `stopped`, `request_limit`, `runtime_limit`,
`spend_limit`, and `spend_estimate_exceeded`.
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

## Optional USD admission policy (version 1)

A fresh authorization can include an operator-supplied `spend` object. The UI
leaves prices blank: an exact preview-model/plan price must not be inferred from
a similarly named model. The current MiniMax documentation lists
[Flash Preview as M Plan/Code only](https://platform.minimax.io/docs/api-reference/text-chat-openai);
its [pay-as-you-go pricing](https://platform.minimax.io/subscribe/token-plan?tab=api-enterprise)
does not establish this account's effective preview-model rate. Rates, cache
premiums, context bands, service tier and subscription quota must be checked for
the actual account. No metadata check or price entry calls a model.

```json
{
  "spend": {
    "currency": "USD",
    "budget_usd": "1.00",
    "reserve_usd": "0.10",
    "input_usd_per_million": "1.25",
    "output_usd_per_million": "10",
    "price_reference": "Fictional example v1; replace with exact model/plan pricing"
  }
}
```

All amounts are decimal strings, at most six places and at most USD 1,000,000.
Budget and per-attempt reserve must be positive. Internally, integer microdollars
avoid floating-point admission errors. The identity-bound authorization freezes
rates, source/version text, policy version and authorization timestamp. This
example is **not MiniMax pricing**. Request/time-only workflows remain supported,
including local generation; no USD policy is silently added to old workflows.
Legacy imported consumption cannot be retroactively treated as free or priced
from a count alone, so it cannot be combined with a new USD budget.

Immediately before every physical attempt, including SDK-adapter retries,
corrections, graph memory and concurrent phases, the same SQLite transaction
checks `estimated + unresolved reservations + next reservation <= budget`.
The transaction increments both the request count and the reserved amount before
transport. Insufficient funds block that request with `spend_limit`; a refund
from another request does not silently resume the workflow. Already admitted
results can still finish. Reservations survive worker crashes and restart.

A complete, valid token receipt replaces that attempt's reservation with the
rounded-up estimate. Anthropic cache-read and cache-write input tokens are added
to uncached input; OpenAI input and output totals already include cached and
reasoning tokens. All input uses the supplied input rate; use a rate that covers
any cache-write premium. Missing, partial, negative, fractional, nonfinite or
malformed token counts retain the entire reservation. No automatic refund is
made for timeouts, uncertain delivery, HTTP failures without usage, or cancelled
local work. Repeated completion notifications cannot settle twice. Late usage
settles against the original workflow even after Stop or a new epoch.

An estimate greater than its reservation records the overrun and closes
admission with `spend_estimate_exceeded`. Actual estimates remain visible even
above the total budget. Other admitted requests may still accrue cost. Stopped
or expired state is never reopened by reconciliation. Renewal explicitly supplies
`budget_usd`, covering prior estimates, unresolved reservations and another
request; it retains the original rates/reservation and all history. An operator
who needs different pricing or reservation assumptions must begin a new workflow
and retain the previous receipt. Renewal does not generate or retry anything.

**Guarantee:** admission is limited using the operator's reservation and pricing
assumptions. This is **not a provider invoice cap**, preflight token forecast or
subscription-quota enforcement. The reservation is a chosen allowance, not a
verified maximum request price. Provider-specific charges, wrong/stale rates,
output beyond assumptions and unresolved delivery may cost more. No server-side
tool, media, separate embedding or secondary-provider billing is supported by
this policy. Use provider-side account controls where a hard billing cap is
required. `billing_amount` remains null.

The existing status endpoint is the receipt: it includes frozen pricing/history,
per-attempt reservation/estimate/overrun, aggregate estimated/reserved/available
microdollars, unpriced attempts and the guarantee label. It contains no prompts
or provider keys. The UI shows these values after reload and before renewal.
Tests use fictional rates and no hosted inference; they cover separate-process
concurrency, retries at the transport boundary, cache accounting, Stop/late usage,
renewal/idempotency, overrun and persisted restart state.
