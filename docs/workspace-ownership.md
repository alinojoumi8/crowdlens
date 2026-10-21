# Private workspace ownership (B07)

The local/private, fictional-data pilot uses one private workspace per OIDC account.
The workspace ID is the immutable server-side `auth_users.id` resolved from the
session. Requests cannot select it. Administrators have account-management powers
but no cross-workspace content bypass. Tester application access stays blocked
until B08 administrator-owned quotas are implemented. No real IdP or external
hosting commitment is introduced here.

## Authorization and persistence

`AUTH_DB_PATH` contains `workspace_resources`, keyed by resource kind and ID, and
`workspace_audit`. Creation registers an immutable owner before artifact publication.
A failed creation can leave an unused owner entry; the ID cannot be reused or
transferred, even after deletion. Missing owners and missing execution context fail
closed in OIDC mode. Identity recovery must preserve issuer/subject and account ID.
Never recreate accounts to recover their content.

Projects, cases, versions, graphs, simulations, tasks, reports, proposal revisions
and workflow allowances are independently registered. Document files inherit their
project/case boundary; graph nodes, edges, source chunks and agent memories inherit
the graph boundary. Review packets inherit their proposal and parent report.
Exports and logs use the owning report/simulation/project. Source lookups check the
graph; direct node UUID lookup resolves and checks its actual graph owner. Shared
extraction, embedding and decision cache keys include the workspace.

The request gate rejects foreign resource references in route parameters, repeated
query/form values, JSON bodies and workflow headers before endpoint side effects.
Lists filter owners before applying limits. Managers and SQLite/graph methods also
check ownership, including direct worker calls. Parent links cannot cross workspaces.
Foreign and unowned request IDs receive the same generic 404. API access is audited by account and endpoint; denials include resource identifiers,
without source text. Access-audit storage failure falls back to an operator error
log and does not turn a completed write into a failed response or weaken a denial.
Owner creation and its audit remain one transaction. Ownership lookup failure
stops the operation; permission denials bypass ordinary fallback/retry handlers.
This is application authorization over shared stores, not separate databases or OS
users per tenant. Shared infrastructure capacity and timing are not concealed.

Thread jobs retain ContextVar ownership. Trusted subprocess launchers pass the
workspace ID and ownership database; workflow/task validation rechecks their owner.
Neither the workspace environment nor a Python maintenance scope is exposed through
HTTP. Startup migration, lease recovery and process shutdown are internal maintenance
operations and must inspect all workspaces. They do not authorize an administrator
request to read another workspace. One app/identity configuration per process and
one Gunicorn worker remain the supported runtime. Host/filesystem access is trusted;
this boundary does not protect against an operator editing databases or environment.

## Legacy data and restore

Use a clean fictional dataset for the pilot. Existing unowned records stay available
only to the trusted loopback `AUTH_MODE=local` operator and are invisible in OIDC
mode, including to the first administrator. Startup migration preserves old files
and IDs but does not infer ownership from email, filenames or who signs in first.
There is no HTTP adoption/transfer endpoint or automatic legacy assignment.

If an explicit legacy assignment is needed later, stop writers, back up the complete
store set, inventory the entire linked case/project/graph/task/report/proposal/workflow
closure, confirm its single intended account, and review an assignment manifest.
Conflicting or ambiguous links must stay inaccessible. Implement and test that
separate offline migration before executing it; this change provides no bulk-claim
command and assigns none of the retained private material.

Follow [coordinated backup](coordinated-backup.md), including `AUTH_DB_PATH` and
sidecars even when outside uploads. Restore identities, owners, artifacts, control
state and Neo4j together. Missing ownership cannot be repaired by copying artifacts
alone. Tests reload a SQLite ownership backup and verify original access plus foreign
and legacy denial; they do not establish a hosted disaster-recovery rehearsal.

## Verification

`backend/tests/test_workspace_ownership.py` uses fictional Alice/Bob fixtures,
real Flask request middleware, actual SQLite/files, background threads and a Python
subprocess. Both API users are test-only administrators so passing tests cannot rely
on the tester blanket denial. Coverage includes scoped lists, file reads/writes and
deletes, parent substitution, downloads, graph-node UUIDs, workflow Stop/renewal,
proposal/revision/review access, caches and restored/legacy records. Graph transport
and inference are mocked; no provider calls are made.
