# Administrator-owned quotas (B08)

OIDC app startup requires the durable control database. Quota mode is persisted
there; startup against a managed database fails if OIDC is disabled. New OIDC installations
start closed: no global or workspace allocation, pricing or paid allowance is
invented. The existing trusted local operator mode is unchanged for databases
that have never enabled managed quotas. Tester application access remains gated
pending rollout acceptance. No provider call or deployment is implied by setup.

Each account has one private workspace, so its allocation is both per-user and
per-workspace. The global allocation covers the server's single configured
provider account and all workspaces. Alternate providers, remote embeddings and
optional secondary-provider modes are unsupported; do not enable them for this
pilot.

## Configure through the authenticated same-origin API

An administrator session (including the existing MFA requirement) and its
`X-CrowdLens-CSRF` header are required to change settings. There is no public
quota bootstrap or tester write endpoint. Account IDs are available from the
administrator account page. Administrators can manage another account's limits
without gaining access to that account's content.

- `GET /api/execution/quotas`: the caller's workspace usage and shared admission
  state; other workspaces' usage is not exposed.
- `GET|PUT /api/execution/quotas/global`: global policy and usage.
- `GET|PUT /api/execution/quotas/<account_id>`: an existing account's policy and
  usage. Settings changes are audited with server-resolved administrator ID.
- `GET /api/execution/configuration`: whether pricing/quotas allow authorization.

PUT replaces a policy. Every field below is required; unknown fields, booleans
as numbers, negative/fractional limits, and limits above 10^12 are rejected.
**Zero denies admission; it never means unlimited.** This example is a closed
fictional fixture, not MiniMax pricing or permission to spend:

```json
{
  "admission_open": false,
  "limits": {
    "requests": 0,
    "daily_requests": 0,
    "estimated_micro_usd": 0,
    "daily_estimated_micro_usd": 0,
    "operations": 0,
    "daily_operations": 0,
    "storage_write_bytes": 0,
    "active_work": 0
  },
  "pricing": {
    "currency": "USD",
    "reserve_usd": "0.05",
    "input_usd_per_million": "1",
    "output_usd_per_million": "10",
    "price_reference": "Fictional fixture rates v1, not provider prices"
  }
}
```

Only the global policy has `pricing`. Omit that field entirely for account
policies. The server binds global pricing to its configured provider, model and
endpoint. Before opening admission, the operator must choose finite request,
operation, storage, active-work and estimated-spending allocations and verify
pricing/reservation assumptions for the exact permitted provider/model/plan.
Rates can be zero for an explicitly verified inclusive plan; reservations stay
positive. Changing provider identity closes new admission until pricing is
reviewed and saved again.

Clients may request smaller workflow ceilings/budgets. Client-supplied rates,
references and reservations never control shared accounting. Each physical
attempt, including retries, takes one request and a reservation under the
current administrator pricing in the **same SQLite transaction** as workflow
admission. Token usage settles that attempt's saved pricing once. A workflow's
older saved estimate can differ from shared accounting after an administrator
changes pricing; both remain estimates, separate from provider billing.

## Counters, recovery and emergency closure

Lifetime counters span all workflows and renewals. Daily request/operation
counters reset at 00:00 UTC. A daily cost check includes that UTC day's known
estimates **plus all unresolved reservations from earlier days**. Unknown usage,
in-flight attempts and failed deliveries retain their reservations across Stop,
renewal, restart and midnight. Complete late usage settles into the original
admission day. An estimate exceeding its reservation automatically closes global
admission and records an audit event; review assumptions before reopening it.

Starting/renewing allowances consumes the shared operation allowance; idempotent
replays do not. Potentially expensive API requests and physical embedding attempts
also consume it. Cheap workflow/task/progress polling is excluded. Synchronous
requests and pending/processing background tasks share active-work capacity;
request admission uses the task runtime's cross-process fence. A request can hand
its slot to its task. Terminal task status releases capacity. A restart never
assumes an unfinished HTTP operation or pending task completed: abandoned HTTP
slots remain conservatively occupied and need operator investigation before
increasing capacity. Existing task ownership recovery remains authoritative.

Set the global policy's `admission_open` to false to stop new model/embedding
calls and new work. Stop, deletion, late usage settlement and bounded cancellation
repairs remain available. Existing readable artifacts can still be read within
the operation allowance. No in-flight provider request is promised to cancel or
be free. HTTP 429 quota responses retain an actionable administrator/daily-reset
message; a new allowance is not a recovery mechanism for shared exhaustion.

Pre-quota workflows cannot admit calls or be renewed in managed mode. Use fresh
fictional projects and new authorization; no legacy ownership, outstanding
private usage or provider-billing history is adopted automatically. Keep
`AUTH_DB_PATH`, the control database and artifacts in the same coordinated
backup/restore set. Restoring only one database is unsupported.

## Storage boundary

`storage_write_bytes` is a **cumulative logical write allowance**, not current
disk occupancy or an OS filesystem quota. Managed upload/artifact writers check
UTF-8/binary bytes before publication; concurrent publications charge atomically.
Overwrites, retries, failed writes after reservation and deletions never refund
bytes. Atomic proposal/revision writes and logical Neo4j write parameters are
charged too. Exhausting the allowance leaves existing content intact. Internal
identity/control metadata, bounded cancellation repairs, host operational logs,
database/index overhead and temporary request parsing are separate host-capacity
concerns; the request/operation caps also bound new metadata admission.

Managed simulation launch uses the fixed `quota_runner.py` bootstrap. Only that
child interpreter installs quota-aware file/Path/descriptor writers and SQLite
connections/cursors; server-wide Python I/O is not patched. SQLite logical
mutations are charged before execution, including worker threads and retries;
identity/control databases are exempt from recursive metering. Unsupported bulk
copies, raw descriptor exports and custom SQLite factories/cursors fail closed.
Bytecode cache writes are disabled in the managed child. The parent drains
stdout/stderr through a bounded pipe and charges each chunk before log
publication. Storage exhaustion stops the owned child and records a quota reason.
A completed run retains its outcome when only its idle environment closes.

Tests exercise real OS subprocesses, file publication, SQLite worker writes,
the installed OASIS schema initializer, and raw stdout capture. Autonomous
OASIS/model behavior is not established by these synthetic boundary checks.
B09 input/parser bounds, B12 execution controls and host disk/capacity gates are
still required before tester access. This quota implementation is not a physical
disk-full, CPU/memory isolation or external-beta claim; SQLite/Neo4j native
overhead and host operational writes need separate capacity limits.

## Periodic provider reconciliation

After each UTC day with provider activity and before increasing allocations,
the administrator should compare global admitted requests, known estimates and
unknown reservations with the provider account's statement/dashboard. Use the
provider's reporting period and note inclusive plans, delayed usage and other
applications sharing that provider account. Do not put credentials or private
source content into references.

`POST /api/execution/quotas/reconciliation` records an immutable comparison:

```json
{
  "period_start": 1792454400,
  "period_end": 1792540800,
  "reported_micro_usd": 0,
  "reported_requests": 0,
  "reference": "Synthetic example only; replace with a non-secret statement reference"
}
```

Periods are UTC Unix seconds with an exclusive end, no later than the current
time. `GET` returns the latest 20 receipts. Supplied provider figures carry
administrator-supplied provenance, not independent verification. A comparison
does not release unknown reservations, reset counters or overwrite per-request
usage. No automatic provider request, scheduler, paid service or dollar-invoice
guarantee is added. Local tests use synthetic statements only.
