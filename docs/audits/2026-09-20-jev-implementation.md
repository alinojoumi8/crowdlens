# Jev implementation and rollout record — 2026-09-20

Implemented first-release plan Tasks 1–5 on `codex/jev-decision-services`. Changes are committed locally, not pushed. Tasks 6–7 remain optional experiments.

## Verification

- Full backend suite: 224 passed. Frontend: 11 unit and 2 component tests passed. Production frontend build passed.
- Final independent review found four Important issues and one Minor, regraded Important because malformed provider answers must always preserve fallback behavior. All five were reproduced with failing tests, fixed, and verified in the full suite. No deferred review findings.
- Healthy Docker app, Neo4j and embeddings after deployment; `/api/status` reports MiniMax-M3, Jev `jev-1.13.0`, and three available shadow features.
- Runtime check used existing provenance-bearing Neo4j records, retrieved 2 facts and 2 source cards, produced a supported shadow check, and persisted 2 decision records. It did not mutate graph data.
- Live synthetic evaluations and save/reload workflow results are documented in `docs/jev-evaluation.md`. They are connectivity and boundary checks, not a domain benchmark or proof of promotion readiness.
- Local canonical `TYPESAFE_API_KEY` configured from the supplied key. Other model settings preserved; local Jev modes set to shadow.

## Implementation rulings and tradeoffs

- Ruling: Work in an isolated detached worktree and fast-forward the task branch after review — preserve the live checkout until tested — cost if wrong: integration coordination.
- Ruling: Implement replay/live evaluation with honest synthetic fixtures and leave local features in shadow until reviewed domain data passes gates — production-quality labels cannot be manufactured — cost if wrong: benefit is delayed.
- Task 1: Ruling: Use a process-wide concurrency cap of two instead of a per-simulation registry — bounds all features and avoids unbounded run-lock storage — cost if wrong: parallel runs fall back more often.
- Task 3: Ruling: Keep the original retrieval plus a bounded 30-item shadow shortlist — changing hybrid normalization can change the baseline even without applying Jev — cost if wrong: one extra database retrieval per active search.
- Task 3: Ruling: Reuse existing SearchService limit support and run reranking entirely in GraphToolsService — avoids changing transaction internals — cost if wrong: direct storage callers do not receive reranking.
- Task 5: Ruling: Ship synthetic boundary fixtures and replay/live tools without manufacturing the requested large domain benchmark — no reviewed case labels are supplied — cost if wrong: promotion requires additional evaluation work.
- Task 5: Ruling: Compare Jev against an M3 typed-judgment comparator and retain the original shortlist order for retrieval analysis — M3 agreement is not ground truth and production retrieval is hybrid — cost if wrong: comparator latency is not full workflow latency.
- Final: Ruling: Keep Tasks 6-7 outside this release — they were explicitly optional experiments — cost if wrong: stance and economy replacement remain unavailable.
- Final: Ruling: Keep domain accuracy, calibrated thresholds and savings unclaimed — synthetic tests cannot establish them — cost if wrong: activation and measured benefits are delayed.
- Final: Ruling: Leave extraction-cache migration and OASIS tool-history work outside Tasks 1-5 — they are separate baseline audit findings — cost if wrong: those existing limitations persist.
- Final: Ruling: Treat claim checks as advisory associations, not exhaustive fact identification or document-truth certification — the implemented source-check boundary is explicit — cost if wrong: an unassociated false claim can escape semantic checking.
- Final: Ruling: Verify live deployment and the full suite locally because the reviewer did not rerun them — independent review covers code while runtime evidence comes from this executor — cost if wrong: runtime verification lacks a second operator.

## Remaining evaluation work

Create domain-reviewed development and held-out sets before turning a feature on. Initial targets remain 50 interview scenarios, 100 retrieval queries, and 200 source claims. A complete multi-agent simulation and end-to-end generated report have not been benchmarked for this release. Extraction-cache model identity and OASIS structured tool history remain separate findings in the original audit.
