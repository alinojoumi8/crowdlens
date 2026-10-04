# ECC workflow plan for CrowdLens

Status: Milestone 1 documentation preserved. Milestone 2 H1 recovery is fixed
and locally verified at `33d87c8`, with subsequent call-site repairs recorded in
[the integration review](audits/2026-10-02-h1-integration-review.md). Operational,
model and deployment gaps remain.
Milestones 3–5 have local implementation and evidence recorded in the
[consolidated handoff](audits/2026-10-02-ecc-milestones-3-5.md). Use its separate
status table: deterministic checks do not complete model/human quality, remote CI,
or existing deployment verification.
The [2026-10-03 control/recovery follow-up](audits/2026-10-03-control-recovery.md)
reproduces the fictional live test's failures and repairs settings, Stop,
terminal report polling and whole-workflow request/time admission on `34ad6d2`.
Synthetic checks pass. A subsequent user approval enabled the
[actual MiniMax browser tests](audits/2026-10-03-live-cedarbrook.md): one revision
saved/reopened after three repairs, then a fresh `1f61571` run completed its report
but all three proposals were blocked on that earlier candidate. The subsequent
[report reliability follow-up](audits/2026-10-03-report-reliability.md) completes
fresh accepted-child reload/history on `7f4d68e`. Independent model quality, human
labels, remote CI and deployment verification remain open.
Prepared: 2026-10-02. Source baseline: `main` at `34275b7`.
Skill reference: the original plan used ECC 2.2.2 `ecc-guide`; this execution
read the installed ECC 2.2.3 instructions for each assigned milestone. Recheck
installed instructions when starting another task.

## Recommendation

Use ECC as a small set of repeatable engineering workflows around the existing
application. Start by reconciling capabilities and the roadmap, then audit agent
behavior and recovery, establish evidence-quality evaluations, and improve the
user journeys based on those findings. Apply verification to every code change.

CrowdLens already has a Vue 3/Vite frontend, a Flask backend, Neo4j graph storage,
a SQLite control plane, filesystem artifacts, local and optional hosted model
adapters, and evidence-first report proposals and immutable revisions. This plan
builds on that architecture and the existing pytest, Node test, Vitest, and GitHub
Actions checks.

Milestone 1 is recorded in [the capability manifest](product-capabilities.md).
The reconciled roadmap distinguishes the implemented status endpoint, partial
memory persistence, and existing tests from remaining operational and quality
verification. Existing tests do not automatically prove full end-to-end coverage
or complete persistence.

## How to use ECC here

- Invoke a named skill in a normal Codex request, with a bounded goal and expected
  output. The examples below are prompts, not shell commands.
- Use the installed plugin skills directly. This plan requires no additional
  installer, copied command collection, or hook configuration.
- Follow the project's codebase knowledge graph instructions: prefer `search_graph`,
  `trace_path`, `get_code_snippet`, then complex graph queries; use `get_architecture`
  for an overview. Use
  file searches for documentation/configuration or when graph results are
  insufficient; verify that the index covers recently merged code.
- Adapt examples to Vue and Flask. Record absent lint, type-check, or coverage
  tooling as gaps; do not report those checks as passed or introduce a framework
  migration just to match a skill example.
- Preserve storage compatibility, original reports, and human review of generated
  revisions. Label simulated behavior separately from source-backed facts.

## Ordered milestones

| Order | ECC skills | Work in this repo | Deliverable and completion evidence |
| --- | --- | --- | --- |
| 1 | `product-capability` | Map upload → graph → scenario → simulation → report → proposal review. Reconcile README and ROADMAP against routes, persistence, tests, and current runtime behavior. | One `docs/product-capabilities.md` manifest, updated ROADMAP/README, and evidence for each implemented/partial/planned capability. |
| 2 | `agent-architecture-audit`, `production-audit` | Trace prompt assembly, provider adapters, tool execution, source retrieval, memory scope, retries, restart recovery, and revision publication. Audit the local deployment boundary and backup/recovery paths. | A dated report in `docs/audits/`, severity-ranked findings with code evidence, and targeted fixes with regression checks. Update the existing architecture/recovery docs as needed. |
| 3 | `eval-harness`, `ai-regression-testing` | Define report-quality and lifecycle evaluations before changing prompts or agent logic. Test relevant source selection, unsupported claims, conflicting sources, missing evidence, and isolation between cases. | Versioned synthetic fixtures and `docs/evaluations/evidence-quality.md`, with a baseline, deterministic assertions, human-review rubric, and recorded failures. |
| 4 | `browser-qa` | Exercise upload, graph readiness, simulation progress, report inspection, proposal review, and revision reopening on the local preview. Include loading, empty, error, keyboard, and responsive states. | A dated QA report, screenshots at 375/768/1440px, and fixes to confirmed failures. Establish a visual baseline before claiming visual regression passes. |
| 5 | `verification-loop`, `production-audit` | Validate each resulting release candidate from a clean environment and the exact commit being delivered. Review runtime limits, documentation, recovery, and remaining risks. | Passing applicable checks, current CI evidence, a release recommendation with explicit limits, and an actionable remaining backlog. |

Run milestone 1 first. Milestone 2 determines which corrective work has priority;
milestone 3 defines the quality boundary for agent changes. Milestone 4 verifies
the resulting user behavior. Milestone 5 applies to every candidate release,
not only the end of this plan. Keep fixes in small, reviewable commits or PRs.

### Milestone 1: capability contract

The capability manifest should distinguish product promises, fixed invariants,
architecture preferences, and unresolved decisions. For every capability record:

- Actor, input, visible outcome, and required states/transitions.
- Interface and storage ownership, including failure/recovery behavior.
- Implementation evidence and verification evidence, with remaining gaps.
- Status: implemented, partial, planned, or unverified.

Retain one manifest rather than creating a parallel PRD/SRS stack. Link to
[architecture](architecture.md), [evidence-first reports](evidence-first-reports.md),
and [storage recovery](control-plane-migration.md) for detailed contracts.

Suggested first request:

> Use ecc:product-capability for CrowdLens. Create docs/product-capabilities.md
> from the existing workflow and code evidence, reconcile ROADMAP.md and README.md,
> and identify the highest-priority verification gaps. Keep application behavior
> unchanged during this milestone.

### Milestones 2–3: agent integrity and measurable quality

Prioritize these boundaries during the architecture audit:

1. Evidence retrieval stays within the selected graph, case, and source version.
2. Tool results and generated assertions retain distinct provenance.
3. Retries and fallback model calls are bounded, visible, and cannot silently
   replace accepted output or duplicate persistent writes.
4. Proposal acceptance creates a separate immutable revision with review status;
   original reports remain unchanged, including after interrupted writes/restarts.
5. Provider selection, embedding dimensions, and saved-run configuration agree.

For evaluations, start with a small synthetic packet containing a supported claim,
an unsupported claim, conflicting sources, and an unrelated case. Record fixture
hashes, code commit, model/configuration, grader version, and run count. Use code
assertions for scope, schemas, revision immutability, and lifecycle behavior; use
explicit human adjudication for ambiguous factual support and omissions.

Separate structural validity from factual quality. Track first-attempt success,
repeat-run stability, source-attribution accuracy, unsupported-claim rate, review
effort, latency, and model calls. Establish a measured baseline before setting
quality or performance thresholds. Model-generated scores are supplementary
evidence; synthetic evaluations cannot establish real-world forecast accuracy.

Use the `eval-harness` evaluation methodology with the repo's existing runners.
The ECC utility's candidate-execution gate currently refuses execution because
verified OS containment is unavailable; its receipts/static checks must not be
treated as isolation or promotion evidence. Do not build this plan around that gate.

## Verification for implementation work

Use `verification-loop` as a checklist adapted to the actual package scripts.
The baseline commands, from the repository root, are:

```bash
UV_PYTHON=3.11 npm run check
npm audit --audit-level=moderate
npm audit --prefix frontend --audit-level=moderate
docker compose config --quiet
git diff --check
```

Compose validation needs the documented environment configuration. Use disposable
test configuration for clean-environment checks; preserve the user's local secrets
and data. CI currently uses Python 3.11 and Node 22, frozen backend dependencies,
frontend unit/component tests, the production build, both npm audits, Compose
validation, and an image build. A local build alone does not cover all of CI.

For relevant changes, also verify:

- Credential-neutral backend execution and affected API contracts.
- Browser behavior on a running preview with synthetic data.
- Restart, retry, and failed-write behavior when changing persistence/lifecycle code.
- Original artifact hashes when changing proposals or revisions.
- Applicable CI on the exact PR head before merging.

Report fresh results separately from historical audit evidence. Add regression
tests for demonstrated bugs and critical behavior changes; documentation-only
edits need link, wording, and diff checks rather than an application test rerun.

## Skills to defer

| Skill/workflow | Reason |
| --- | --- |
| `repo-scan` | The ECC entry is an external-skill installation pointer, not an executable audit. The existing knowledge graph and targeted inspection cover the initial inventory. |
| `agent-eval` | Compares coding assistants through an external CLI; it does not measure CrowdLens simulation or report quality. |
| `delivery-gate` | A Claude Code Stop hook checking session hygiene. It is not a Codex application-release gate or a replacement for CI. |
| `orch-change-feature`, `orch-fix-defect` | Optional future orchestration lanes with their own engine and gates. Direct scoped skills are sufficient for this initial plan; read the engine before opting in. |
| Greenfield scaffolding and hosted/multi-user rollout | Current work should strengthen the existing local application. New product scope needs its own capability contract. |

Hook trust and external tooling installation are separate configuration decisions.
Keep evaluation fixtures local and synthetic by default; hosted evaluations require
an explicitly chosen provider, permitted inputs, and a bounded run budget. Existing
[Jev evaluation boundaries](jev-evaluation.md) continue to apply.

## Definition of a useful outcome

ECC adoption succeeds when the roadmap matches demonstrated capabilities, agent
changes have measurable regression evidence, recovery and review boundaries are
verified, and each delivered change includes current checks and updated docs.
The number of installed skills or generated planning files is not a success metric.

## Historical Milestone 2 audit snapshot — 2026-10-02

The following paragraph describes the original audit before H1 and later work.

See the [agent architecture audit](audits/2026-10-02-milestone-2-agent-audit.md).
Five high boundary failures have isolated fixes and regression evidence. Generic
tasks still retain processing state after their writer exits: remediation is
incomplete until owned recovery is implemented and verified. The running image
differs from main and remains unchanged. Synthetic HTTP/Neo4j proposal integration
passed with a deterministic drafting substitute; actual local upload/ontology is
blocked by the missing generation model. Full workflow and report quality remain
unverified. No push, merge, deployment change or later milestone was performed.

## Initial H1 follow-up — 2026-10-02

The [H1 remediation addendum](audits/2026-10-02-h1-task-recovery.md) supersedes
the earlier unresolved H1 status for the isolated source. New generic tasks have
persisted worker/attempt ownership, periodic recovery and publication fences.
Real two-process, API/manual-retry and related-state regressions pass; legacy
ownerless tasks remain explicitly uncertain. The fresh full check passed 419
tests and the production frontend build. Existing deployment reconciliation,
full provider workflow and measured report quality remain open. This follow-up
does not declare later milestones or release readiness complete.

## Milestones 3–5 execution handoff — 2026-10-02

The [task ledger](audits/2026-10-02-ecc-execution-ledger.md) records isolated
specialist ownership and local integration commits. The [consolidated report](audits/2026-10-02-ecc-milestones-3-5.md)
identifies the final tested candidate and the subsequent documentation-only commit.
It links the frozen structural before/after baseline, blind human-review materials,
first visual baseline, real storage/cold-restore evidence, fresh dependency/build
checks, and independent AI review findings and repairs.

Remaining actions are bounded: arrange a suitable generation model with explicit
runtime/input constraints; obtain independent human labels; authorize and run
exact-candidate remote CI; separately reconcile the existing deployment. Define
monetary admission and retention/backup policies before expanding those
promises. No prompt tuning, model-quality improvement, main merge, deployment,
or human approval is implied by successful synthetic verification.

## Control/recovery follow-up — 2026-10-03

The [repair audit](audits/2026-10-03-control-recovery.md) identifies historical
browser source `242b899`, the new tested source `34ad6d2`, retained fail-first
regressions, durable request/time accounting and explicit recovery semantics.
It records 545 passing tests/build, 504 repeated structural executions, H1 and
synthetic cold restore, isolated browser suites and independent review scope.
These results do not transfer prior image/CI/service checks to the new source.

The [previous-run accounting](audits/2026-10-03-bike-lane-request-accounting.md)
accounts for all 30 admitted requests with stage-assignment and billing unknowns.
The [visible acceptance plan](visible-browser-acceptance.md) froze the original
fictional input/requirement and supported settings. That repair-only follow-up
made no paid calls. Subsequent explicit approval enabled the separate real tests
below; the historical 30-request allowance was not reused.

## Actual browser follow-up — 2026-10-03

[The real-test audit](audits/2026-10-03-live-cedarbrook.md) records three minimal
fail-first repairs: visible participant-type selection, structured single-platform
worker events, and original graph/version scope recovery for general reports.
Candidate `1f61571` passed 506 backend, 12 Node and 39 component tests plus build;
independent code review found no blocking issue in those fixes.

The first actual journey used 42 requests and saved/reopened a separate Needs
review child with its parent and other sections unchanged. Its application source
changed between stages, so it is not a fresh single-candidate pass. A separate
unchanged-candidate run used 38 requests, completed actual graph/personas/OASIS
and a three-section report, but all three proposal attempts were safely blocked.
No fresh child was accepted. Both stopped ledgers retain all attempts and unknown
billing amount; no push, main merge or deployment occurred.

Next corrective work is report source/trace provenance, consistent uncalibrated
forecast presentation, precise retained audit diagnostics and real-model draft
contract reliability. Independent human evaluation remains required. Do not mark
Milestones 3–5 complete or transfer prior release checks based on these tests.

## Scoped report reliability follow-up — 2026-10-03

All four [corrective tasks](tasks/2026-10-03-report-reliability.md) are complete
locally on application candidate `7f4d68e`: precise private proposal diagnostics,
original/action report provenance and frozen forecast authority, honest effective
settings/activity/state, and fresh actual MiniMax-M3 visible-browser acceptance.
A bounded counted correction addresses model quote drift while preserving failed
text/findings and the same guards. Full check: 563 backend + 63 frontend tests and
build. The accepted child `report_3d12d343d6fa4c5d86998d8d88ea042a` remains Needs review; parent and unselected
sections are unchanged. Final workflow stopped at 26/90 with no pending calls;
87 earlier partial-candidate attempts remain accounted separately. See [the audit](audits/2026-10-03-report-reliability.md).

The [semantic-review milestone](audits/2026-10-03-semantic-review.md) adds limited deterministic trace checks, preserves unresolved proposal audit findings, and displays current read-only assessments on retained reports. This does not establish general entailment, omissions or independent truth labels.

Held-out collection and browser review preparation are complete: [four actual-model drafts](evaluations/2026-10-03-source-review-v2.md), 0/4 ready, nine requests, unchanged application behavior. Independent human labels and measured reviewer effort remain PENDING; the user will review in the browser. Then run the separately authorized exact-candidate
release/CI/deployment task. This scoped result does not mark original Milestones
3–5 globally complete or transfer their previous release evidence.

## Source coverage repair follow-up

[Source coverage and summary repair](audits/2026-10-03-source-coverage-repair.md) implements bounded companion-document retrieval, source metadata preservation, planned-claim coverage and server-resolved exact summary spans. Final check passes 673 tests and build. Fresh v3 actual MiniMax verification retrieved all eight current originals, with one ready and three blocked proposals after 11 requests; strict guards and original reports are preserved. Independent Astra max review finds all 28 material section facts covered; 31 of 33 claim judgments are supported, one unsupported and one ambiguous. These AI opinions stay separate from still-unmeasured human labels/time. This does not establish broad factual quality or release readiness.

## Claim grounding and summary contract follow-up — 2026-10-04

[Contract completion](audits/2026-10-04-draft-contract-completion.md) requires complete explicit AI source judgments, checks resulting-summary consistency even with edits, and confines server-owned summary replacements to a unique literal selected-section span. Unmapped summaries stay unchanged for review; strict legacy contracts remain compatible. Title-topic retrieval and raw target exports are covered by separate regressions. All 694 tests and the build pass, with independent code review and a visible provider-disabled immutable-revision test. Fresh MiniMax v4/v5 each retain 0 ready out of four attempts (8/10 requests); v5 retrieves all eight originals and preserves all parents, but actual-model JSON, premise and semantic-audit reliability remain unresolved. Human labels/time remain unmeasured. These scoped fixes do not establish factual certification, end-to-end or release readiness. Next: separate development work on provider contract and audit reliability, then new frozen verification cases.
