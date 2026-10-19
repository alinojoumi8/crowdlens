# B07 workspace ownership verification — 2026-10-19

Scope: local/private fictional-data pilot, one workspace per server-resolved OIDC
account, no new paid services. Implemented on `codex/workspace-ownership` from
PR #33 merge `6f84d19b08c6ae8040399ebebc7e287a00dbee97`. No deployment, live model
calls, legacy ownership assignment or real invitations were performed.

See [the ownership contract](../workspace-ownership.md) for persistence, maintenance
privileges, fail-closed legacy behavior and coordinated restore requirements.

## Verification boundary

`UV_PYTHON=3.11 pnpm check` passed with Node 22: **1,113 backend tests**,
**12 frontend tests**, **110 component tests**, and the production Vite build.
`git diff --check` passed. The 19 ownership tests are included in the backend total.

The new suite uses two independent accounts with equal API privileges, real Flask
middleware, SQLite and artifact files. Synthetic API users are administrators so
tests exercise ownership rather than passing on the existing tester blanket denial.
The 19 ownership tests cover:

- Immutable owners; foreign, missing and legacy IDs; cross-workspace parents.
- Lists, direct SQLite access, extracted documents, files, reports and deletion.
- Authenticated API reads, downloads, mutations, repeated query values and overrides.
- Workflow idempotency, resolution, Stop, renewal and resource binding.
- Background task attempts, actual graph-memory thread and concurrent profile pool.
- Proposal, revision and human-review access.
- Graph-node UUID checks, graph search/source entry points and deletion, using a
  mocked Neo4j transport.
- Disk and in-memory embedding/extraction caches, workspace-bearing subprocesses,
  owner-registry SQLite backup/reload and full OIDC application startup migration.
- Generic 404 control flow through ordinary exception fallbacks; owner lookup
  failure; audit storage failure after writes and during denials; bounded list
  ownership queries and an empty-workspace fast path.

No inference transport or live Neo4j test was used. Full hosted CI and container
acceptance remain the PR delivery step. Lint and typecheck scripts are not configured.

Chromium checked the revised tester-account notice, 390px layout without horizontal
overflow, and successful sign-out in an isolated loopback fixture. Screenshot:
[tester account](screenshots/2026-10-19-workspace-account-mobile.png). The temporary
fixture was stopped after inspection.

## CodeRabbit disposition

CLI 0.9.0, authenticated, reviewed an isolated clone whose origin is the canonical
`alinojoumi8/crowdlens`. Shared checkout remotes and unrelated local files were not
changed. No paid credits or overage flags were used.

First completed review: two Minor findings fixed (denials swallowed by ordinary
exception handlers; one ownership connection per list row). One Major thread-context
warning dismissed after inspecting existing per-job `copy_context().run` launchers
and executing the actual graph-memory/profile workers under both workspaces.

Second completed review: Major audit-error response corruption reproduced and fixed;
Minor empty-owner table scan fixed. The Major new-record authorization warning was
dismissed: creation registers server-generated IDs before storage puts. Actual
manager, API and full application-startup tests verify that order. Allowing unknown
puts would permit accidental legacy adoption and is deliberately rejected.

Final CodeRabbit follow-up completed successfully with zero findings on the
implementation. No confirmed review findings remain unresolved. The final test
logging assertion uses a wrapped logger because application logging does not
propagate to pytest caplog; its failure injection and behavior assertions passed.
The report and screenshot received a focused documentation review.

## Remaining release gates

Tester application access stays closed pending B08 administrator-owned quotas.
Real IdP configuration and MFA/recovery adoption are still open. This is application
isolation over shared stores on one worker, not separate tenant databases, a hosted
security certification, a full Neo4j restore rehearsal or complete account erasure.
The next delivery step is an implementation PR and hosted CI; the next application
feature is B08. The existing Confluence backlog remains authoritative for wider beta
work; the current unfinished CrowdLens/MiroFish Jira search returned no matches.
