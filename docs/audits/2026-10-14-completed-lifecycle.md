# Completed-run lifecycle preservation

Closing a workflow previously rewrote a completed simulation to stopped and
replaced its completion timestamp. The idle-worker monitor could also classify
its later process exit as a new failure. Closure now preserves completed, failed
and stopped outcomes, timestamps and diagnostics while releasing local workers.
Running/starting/paused cancellation still becomes stopped. Completion events are
accepted only for active runs, so late events cannot upgrade cancelled or failed
runs or refresh a completed timestamp.

Lifecycle mutation and final monitor processing share the existing reentrant task
publication gate. Workflow admission closes before cancellation. Task ownership,
epoch checks, process-object identity and stale-publication fences remain in
place; persisted PIDs are not used to signal unknown workers. The legacy Stop API
also retains a completed simulation's manager status. Graph-memory interruption
remains recorded separately without replacing a completed run's diagnostic.

Validation: 16 new provider-free cases cover repeated idle closure, zero/nonzero
process exit, active cancellation followed by late events, cleanup exceptions,
legacy API status, and real control-database closure with admission denial,
byte-equivalent persisted outcome and revoked-owner write rejection. The full
local check passed 987 backend cases, 101 frontend tests and the production build.
Expired/closed allowances also terminate completed idle workers before releasing
their tracking, with a repeated process-identity check protecting replacements.
Existing replacement-owner, recovery and
publication-order tests passed. Independent AI subagent review reported no
blocking findings and independently passed the affected control suites.

Historical canary state, actions, reports and the closed inference allowance are
not rewritten. No hosted generation was performed. Exact-revision CI, image smoke
and deployment verification receipts are recorded separately in Confluence and
/home/ali/.local/state/crowdlens/lifecycle-20261014/.
