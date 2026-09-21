# Full-population interview evaluation

Implemented bounded, atomic scoring of the full candidate population (`interview-v3`). Each request remains within the gateway's 30-candidate and byte limits. The application admits at most 300 profiles and 16 batches and checks a 20-second population deadline before/after calls; an in-flight request still has its own timeout. Any failed/incomplete batch or deadline failure discards the entire proposal and uses the existing M3 baseline. No partial ranking is used. Oversized populations or shared context are rejected before network calls.

Questions refer to stable named objects such as `candidates.agent_140`, rather than array offsets. Responses are remapped to original indices. Selection ranks relevance with stable index tie-breaking; profession diversity no longer displaces a higher-scored person. Candidate caps and deadlines are application budgets, not claims about TypeSafe service limits.

## Real 197-profile evaluation

Seven literal identity questions from the same original source pages were evaluated against all 197 existing profile snapshots. These are diagnostic labels, not independent domain review or a new simulation. Both models saw the full population and original-page context.

| Run | Jev exact panels | M3 exact panels | Jev selected correctly | M3 selected correctly | Mean Jev latency | Mean M3 latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial array references | 3/7 | 7/7 | 6/10 | 10/10 | 3933.72 ms | 2057.29 ms |
| Final named references | 6/7 | 6/7 | 9/10 | 9/10 | 3775.91 ms | 2195.49 ms |

Every question in both runs returned all 197 scores successfully. The initial run's adjacent-profile misses motivated stable named references. The second run improves observed Jev selection but is not proof that all positional ambiguity is eliminated. M3 also varied between runs; neither run is omitted. In the final run Jev missed one named plaintiff, and M3 selected a different stock-affidavit profile.

The final Jev run used seven requests per question: 49 calls, 313131 reported input tokens and 21770 output tokens. The initial run used 301770 input and 21770 output tokens. No dollar-cost comparison is claimed; baseline token telemetry was not instrumented for this script.

**Decision: do not promote.** Final accuracy did not exceed M3, latency was higher, and this is one small case with assistant-reviewed labels. MiniMax-M3 remains primary, and all three Jev features remain shadow. Future evaluation needs independent labels, multiple held-out cases, alias/duplicate-person handling, and a demonstrated accuracy or efficiency benefit.

## Reproduction and validation

Private inputs/results are ignored under `backend/uploads/evaluations/jev-real-case/`: `population-pilot.py`, `population-run.json`, `population-decisions/`, `population-keyed-pilot.py`, `population-keyed-run.json`, and `population-keyed-decisions/`. Scripts issue paid provider calls. Both runs are retained.

Final validation: 251 backend tests, 11 frontend unit tests, 4 frontend component tests, and production build passed. Tests include all-197 coverage, stable identity mapping, no partial proposals, preflight budgets, shadow baseline preservation, relevance ordering, and saved summary source checks. Docker rebuilt and deployed. Source-review UI was verified in the browser; application health and shadow settings were rechecked.
