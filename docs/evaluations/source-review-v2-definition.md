# Frozen source-review v2 evaluation definition

Four new fictional held-out case/source splits, separate from v1 parcel fixtures,
Cedarbrook development regressions, private documents and historical prediction
packets. Freeze corpus and this definition before collecting any output. No
application, provider prompt or grader threshold may be tuned using these cases.

Use the unchanged EvidenceDraftingService and its existing ledger/draft/audit
prompts. One attempt per case, no hidden retries or replacements. Model:
MiniMax-M3, existing authorised provider. Maximum 12 requests across all cases
and 900 seconds; per-proposal deadline 180 seconds. No automatic acceptance or
publication. Initial comparison prose is authored evaluation input, not a real
model baseline. This measures source-scoped proposal output, not full report
creation, simulation, graph extraction or E2E reliability.

Predeclared deterministic invariants: only current matching original-source
windows reach the provider; original input report hashes remain unchanged;
provider attempts stay within allowance; raw and parsed responses are retained;
all attempted cases, including blocked/failed cases, stay in denominators.
Report ready/attempted and calls, usage, timings and failures. No target rate is
invented after results. Cost stays unknown without an explicit price schedule.

Independent human review rates precise claim support, attribution, citation
support, conflicting-account handling and omissions against reviewer-authored
source-backed reference facts. Active review time is measured by the reviewer,
not inferred. Preserve nulls and disagreements using the existing strict review
importer. Blank forms must import as PENDING with null rates and timing.

Reviewer packets hide origin, model, findings and design categories. The source
content itself is visible. Keep administrator mapping/results away from reviewers
until their judgments are locked. A successful model audit is not a quality
label. This small fictional sample cannot establish representative accuracy or
forecast calibration. The structural grader and AI fixture author are Codex;
independent human grader identity is pending.
