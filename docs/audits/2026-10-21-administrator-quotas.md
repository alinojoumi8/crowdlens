# B08 administrator-owned quotas — local verification

Date: October 21, 2026. Branch: `codex/administrator-quotas`, based on canonical
main `26397fbe612607adfa814ad20d44bd84c37f6a7f` (merged PR #35).

## Delivered behavior

OIDC installations require durable, administrator-configured global and private
workspace policies. Missing policies and zero limits deny admission. Tester
clients cannot set shared prices, reset counters or grant themselves allocations.
Administrator changes require the existing authenticated MFA session and CSRF
checks and are audited. The provider/model/endpoint identity is bound to pricing.

Physical model attempts and retries reserve requests and estimated cost in the
same transaction as workflow admission. Global and account ceilings survive new
workflows, Stop, renewal, midnight and process restart. Unknown attempts retain
their reservations. Complete usage settles once at the saved rates; an estimate
exceeding its reservation closes global admission. The global switch blocks new
work while Stop, deletion and late settlement remain possible.

Operation admission bounds workflow creation/renewal and expensive non-generation
requests. HTTP operations and background tasks share a cross-process active-work
fence. Pending work and orphan HTTP slots are not assumed complete after restart.
The administrator can record a provider-statement reconciliation without erasing
unknown reservations or resetting counters.

Managed storage writers check a cumulative logical byte allowance before
publication, preserving existing files on rejection. Atomic writers and logical
graph mutations participate. Fixed simulation children install file/descriptor
and SQLite write metering; stdout is charged through a bounded parent pipe.
Exhaustion stops the owned child; closing a completed idle environment preserves
the completed outcome. The server interpreter is not globally patched.

The workflow UI shows server-owned pricing and shared usage, distinguishes
estimates from unknown provider billing, disables the parent start action after
shared closure, and provides an actionable quota error.

## Verification

- The initial OIDC regression reproduced the missing-policy bypass: authorization
  returned 201 where the test required 429. The repaired acceptance suite passes
  all 38 cases, including real OS process races, renewals, UTC boundaries,
  per-account/global limits, unknown usage, pricing changes and restart retention.
- Final `UV_PYTHON=3.11 pnpm check`, with Node 22.23.4, passed 1,151 backend tests,
  12 frontend unit tests, 113 component tests and the production build.
- Root and frontend dependency audits report zero vulnerabilities. Compose
  configuration and staged/working-tree whitespace checks pass. Lint and
  type-check scripts are not configured.
- Boundary tests exercise the real upload writer, concurrent file publication,
  restarted child interpreters, SQLite worker-thread writes, the installed OASIS
  schema initializer, stdout capture and completed-run preservation. Model and
  graph transports are synthetic; no external inference was used.
- Chromium inspected a disposable loopback fixture with fictional identities and
  rates: managed pricing notice, authorization, global closure, Stop, rejected
  renewal, disabled parent start action and a 375-pixel layout without horizontal
  overflow. The persisted shared request counter remained zero. This fixture is
  not the production runtime or a real identity-provider acceptance test.
- CodeRabbit review status: pending the next included free allowance. A review
  attempt in an isolated clone with canonical CrowdLens origin returned a rate
  limit. No paid credits, overages or subscription changes were enabled. This is
  not a completed review or a readiness pass.

## Remaining delivery and rollout gates

The implementation has not been pushed, submitted as a PR, merged or deployed.
Hosted CI and an exact-candidate container build/smoke remain delivery work.
Complete CodeRabbit review before marking the change ready.

`storage_write_bytes` measures cumulative logical writes, not physical occupancy,
database/index overhead or an OS disk quota. Internal control metadata, bounded
cancellation repair, parser temporary files and host diagnostics have separate
capacity requirements. The child meter is not an arbitrary-code sandbox. These
tests do not establish autonomous OASIS behavior, provider invoice accuracy or a
general external-beta acceptance.

Tester project access remains gated. Next application work is B09 external
file/URL/generated-output hardening, followed by the applicable hosting,
networking, B12 execution/capacity, restore and combined acceptance gates. Retain
the local/private fictional-data scope and one-worker runtime. Actual provider
rates, real IdP MFA/recovery and any future live-model test require their own
verified configuration and authorization.

The current Confluence backlog and runbook were checked through the signed-in
browser because the connector timed out. The unfinished Jira query
`statusCategory != Done AND (text ~ "CrowdLens" OR text ~ "MiroFish")` returned no
matches; Confluence still contains unfinished work. The delivery update must
retain the pending review/hosted verification and tester-access gates.
