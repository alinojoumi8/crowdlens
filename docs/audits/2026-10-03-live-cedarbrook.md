# CrowdLens real browser verification — 2026-10-03

Two visible browser journeys used actual MiniMax-M3 generation, local Ollama
embeddings, Neo4j and OASIS. The first reached an accepted, reopened revision
after three repairs. A separate fresh run on the frozen final candidate completed
its report but **all three proposals were blocked**. Full fresh acceptance and
reopening therefore remain **incomplete**. Neither functional completion nor
the report's quality heuristic certifies factual or predictive quality.

The user explicitly approved: “I approve it you can use minimax as much as you
need, also you can use minmax m3.1 flash as well”. Only `MiniMax-M3` was used.
Operator limits remained bounded: 60 total requests for the first workflow,
then 45 for the separately authorized fresh workflow. The first retained all
consumption across explicit time-window renewals. Both ledgers are now stopped:
**80 physical requests altogether, zero in flight and zero unknown usage**.
No main merge, push, deployment, model download or unrelated service change occurred.

## Exact candidate and runtime boundaries

All source is in local branch `codex/crowdlens-control-recovery`, checkout
`/home/ali/.codex/worktrees/crowdlens-ecc-integration/mirofish-local`.

| Boundary | Application identity and result |
| --- | --- |
| First upload, ontology and graph | Reporting HEAD `7d56148518d2c48a01c504a7e4af82bcd7f1a6f3`; source identical to tested `34ad6d2`; fingerprint `fea6ca781b9a175fe9face0055dc195bf7f685551e5af5a5f2b42a5342450006`. |
| Participant selection and first preparation/simulation | `b3a82a6c980e17b347b11963d74ba5210ddda5e0`; fingerprint `591bb6ff05ba77f72addbf58a05098a8533eeaeea389b6eba08f968fe7502abf`. Real OASIS ran, but the old single-platform monitor missed its progress; this attempt remains stopped and preserved. |
| Second actual preparation, simulation and first root report | `75ca8b46b87f19c5c73c0168075a4f373655b5f2`; fingerprint `f41b68a31cf8b858e3b153ce84cf00f7df05d232f8ba06b2507ee706d5fb520f`. Two Twitter rounds and a three-section report completed. |
| First accepted proposal/revision and entire separate fresh run | `1f61571e7788493043f2c929ed9eaf6520a0e7b8`; fingerprint `f72be2d03b85a404abf19992ddf2d86a703848bc50dbe87cf519d8c18a25333f`, `runtime-source-v1`. Fresh source remained frozen through the three blocked proposals. |

The first journey was paused for repairs; it is **not** a single-candidate fresh
E2E pass. The fresh run had a new SQLite/artifact root, an empty Neo4j volume,
one authorization epoch, no time-window renewal and no code changes. Its Stop
receipt records 1,459.203 seconds from first admission; all responses finished
within its 1,800-second window. The UI elapsed counter can continue growing after
Stop; that does not indicate new model calls.

| Isolated runtime | First journey | Frozen-candidate fresh run |
| --- | --- | --- |
| Browser/app | `http://127.0.0.1:18752` | `http://127.0.0.1:18756` |
| Review directory | `/home/ali/Documents/CrowdLens-reviews/2026-10-03-live-cedarbrook` | `/home/ali/Documents/CrowdLens-reviews/2026-10-03-final-candidate` |
| Neo4j | `crowdlens-live-cedarbrook-20261003-neo4j`; HTTP/Bolt `18753/18754` | `crowdlens-live-final-20261003-neo4j`; HTTP/Bolt `18757/18758` |
| Storage/model readiness | Cached Neo4j 5.18 community image, local Ollama `nomic-embed-text`, 768 dimensions, vector indexes online; no pulls | Same cached image/model; zero nodes and zero SQLite migration records before actual upload; readiness checked before generation |

The external launch wrappers supply isolated storage roots and static serving
for the unchanged production frontend. They use the actual application and
adapters, with no generation fixtures, seeded later outputs or intercepted
provider responses. Primary MiniMax uses the Anthropic Messages transport,
Standard tier, zero transport retries; Jev and market lookups are off. Hosted
generation receives only the frozen fictional packet and its derived test context.

## Reproduced repairs and local checks

| Finding | Cause, minimum repair and evidence |
| --- | --- |
| Four-agent cap would omit Daniel and include the municipality | Before the cap, there was no visible participant-type filter. Added a native Agent types multiselect using the existing backend include filter; selected only the types of the four named people. Retained fail-first component tests and [selection finding](evidence/2026-10-03-live-cedarbrook/participant-selection-finding.md). |
| Twitter ran but stayed at zero rounds/actions in the monitor | Legacy single-platform scripts did not emit the structured action log consumed by SimulationRunner. App starts now use the existing shared script with `--twitter-only`/`--reddit-only`, creating only enabled platform logs. Four fail-first tests cover command selection and controlled execution of the real CLI/logger/monitor. [Finding](evidence/2026-10-03-live-cedarbrook/single-platform-monitor-finding.md). |
| General report proposal returned HTTP 409 before inference | General root/config snapshots omit case/version IDs. Admission now retains strict validation, then can recover incomplete legacy scope from exactly one persisted CaseVersion matching original project and graph. Conflicting or ambiguous scope still fails closed. Parent/config files are not edited. Seven tests cover original-version recovery, preservation and rejection cases. [Finding](evidence/2026-10-03-live-cedarbrook/proposal-scope-finding.md). |

Final source `1f61571` passed **506 backend tests, 12 Node tests, 39 component
tests and the frontend production build**. The final frontend bytes match the
served bundles. [Retained test logs and independent reviews](evidence/2026-10-03-live-cedarbrook/README.md)
cover all three repairs. Independent review was read-only AI code review, not
human adjudication. Inspection scripts initially made incorrect assumptions
about legacy platform flags and the CLI round argument; corrected receipts
retain those limitations rather than label them product failures.

Prior image, clean-install, accessibility, evaluation and remote CI results are
not transferred to this changed candidate. The earlier [synthetic control audit](2026-10-03-control-recovery.md)
retains its own exact identity and broader injected-failure coverage.

## Actual workflow results

Both journeys used the unchanged 1,471-byte fictional packet, source SHA-256
`1d79d4a96e4af613f81a1a9195a277ee15753a154d6e2daf48ddd7fae4aaf48b`, and exact
requirement; input fingerprint
`a0cbc3c1a4d5e82a5c02fd14cddc9d7c568b88386b586f5e291a4b26ac568cd4`.
Four named profiles, one profile worker, baseline/one ensemble, two hours,
60-minute rounds, one active agent, Twitter, seed 42, memory off and Prediction/Fast
were selected visibly and checked against saved configuration and execution.
Generated entity-type labels varied between graphs; selection followed actual
types and verified the same four source people.

| Result | First journey | Fresh frozen-candidate run |
| --- | --- | --- |
| Workflow | `wf_47f83c938e6d44888f64dd966ec7afc5` | `wf_00a49d682ed94067984ce6637a300f75` |
| Project | `proj_83707effff70` | `proj_a6ed1026d573` |
| Graph | `88956ccc-ea07-47a7-807d-4fc391ce2489`; 7 nodes/8 relations | `b056ed0d-5897-4565-b5f6-e02553870309`; 5 nodes/10 relations |
| Successful simulation | `sim_499ec61fc52c`; 2/2 Twitter rounds | `sim_9ac5f4ad6a6c`; 2/2 Twitter rounds; zero Reddit rounds/actions |
| Root report | `report_38eb8454832e`; completed 3/3 | `report_6ad447817a9b`; completed 3/3 |
| Proposal/revision | `proposal_95c5c62d4d1a4f10b03dc7c814ee5f51`; section 1 ready, accepted | All three proposals blocked; no child revision |
| Saved child | `report_561a7739a24d480bb5a0ac086eec2cdf`; Needs review | Acceptance/reopen **not completed** |

The first child contains seven source-linked statements, preserves the other two
sections, summary and forecast, and reopened after reload and revision-history
navigation. Its UI disabled repeated Save; an explicit API retry with the same
digest returned the same child without generation. History contains exactly the
root and child. All nine root files remain byte-identical.

The fresh app's actual OASIS command uses `run_parallel_simulation.py` and
`--twitter-only`. Its stale preset passes a CLI maximum of 72, while the worker
uses the minimum with the duration-derived two rounds. Actual action events and
terminal state confirm 2/2; the raw metadata mismatch remains a gap.

| Fresh proposal attempt | Section | Calls | Actual outcome |
| --- | --- | --- | --- |
| `proposal_41906b440b3d49758794e2ea69afb196` | Source facts | 3 | Blocked: `invalid_audit`. |
| `proposal_20eda4b6140f4a2b8541e828165301de` | Source facts, explicit new proposal | 2 | Blocked: `paragraph_kind_mismatch` on paragraphs 0 and 7. |
| `proposal_58c0cb1b68774a998250e844ae64701a` | Uncertainties, separately selected | 3 | Blocked: `invalid_audit`; five nonblocking `premise_unverified` warnings. |

Saving stayed disabled. No validator was relaxed, output rewritten, failed
proposal discarded, parent regenerated or allowance reset to obtain acceptance.
The fresh root's nine frozen files remain unchanged and history contains only
the root. [Fresh receipts](evidence/2026-10-03-final-candidate/README.md) retain
all outcomes. The original audit response is not persisted, so the exact field
behind generic `invalid_audit` cannot be recovered; a new response would not
reconstruct the old one.

## Request accounting and preservation

| Stage | First journey | Fresh run | Combined |
| --- | ---: | ---: | ---: |
| Ontology / graph | 1 / 1 | 1 / 1 | 4 |
| Profiles | 8 | 4 | 12 |
| Time / events / agent configuration | 2 / 2 / 2 | 1 / 1 / 1 | 9 |
| Actual simulation | 4 | 2 | 6 |
| Root report | 19 | 19 | 38 |
| Proposal | 3 | 8 | 11 |
| Total | **42** | **38** | **80** |

Provider-returned totals are 143,946 input tokens, 68,093 output tokens, 181,801
cache-read tokens and zero cache-creation tokens. These fields are retained
without assuming a billing normalization. Unknown usage count is zero; actual
invoice amount remains **unknown**, not zero. Request/time limits are not a
dollar ceiling. Proposal-local telemetry names the Anthropic transport; the
workflow/provider receipts and endpoint identity establish MiniMax.

The earlier 30-request historical run remains separate and incomplete. Its 34
frozen files, the main checkout's five original overlays, 13 first-attempt
simulation files and the failed scope-admission proposal were rehashed unchanged.
Both new root reports and all ten saved-child files are preserved. A final
[read-only verification receipt](evidence/2026-10-03-final-candidate/receipts/final-preservation-and-runtime-check.json)
checks these hashes, both stopped ledgers, their exact source fingerprints and
all 35 disk/served frontend files per runtime. The full external review
directories keep the fictional outputs and isolated runtime; repository evidence
is a selected non-secret copy with SHA manifests.

## Highest-priority remaining gaps

1. **Report provenance and forecast consistency (P1).** Both roots quote graph
   paraphrases as original statements and narrate round-by-round behavior from
   source facts. Actual hosted simulation performed only two calls per successful
   run; the fresh run produced one model post and one DO_NOTHING. First report
   prose says 55–65% versus a 43% panel; fresh prose says about 55% versus 46.5%
   forecast data (47% displayed). Other priors/thresholds lack measured support.
   First quality score 100 and fresh 90/pass do not establish accuracy. Correct
   provenance, ground discussion in actual trace records, define one forecast
   authority and collect independent held-out labels before strengthening claims.
2. **Real proposal contract reliability (P1).** Three fresh attempts failed
   response contracts. Preserve raw audit JSON with precise validation diagnostics
   before another repair/retest; reproduce exact invalid structures, retain
   fail-closed guards and measure success/failure across packets. A successful
   earlier draft is not a reliability estimate.
3. **Action and effective-setting semantics (P2).** First successful database has
   10 posts; fresh has 9. Both display 18 entries, including repeated initial-post
   logs and scheduled-event metadata. Distinguish unique posts, model actions and
   events before using activity for forecast synthesis. Legacy availability flags,
   active/hour and maximum-round aliases, 48-hour generated reasoning, pre-Start
   Running labels and dual-platform/memory wording conflict with effective bounds.
   The planned env tool allowance of one is not enforced; actual Fast code allows
   up to two tools per section. Documented numeric/runtime bounds were enforced.
4. **Completion and release boundaries (P2).** Fresh test-revision acceptance is
   still blocked. Historical-copy paid recovery was not attempted. Exact-candidate
   remote CI, image/deployment reconciliation, broader provider support, monetary
   admission, memory restart continuity and independent human quality evaluation
   remain outstanding.

The saved first child and fresh blocked report remain open in the visible
browser. Both workflows block new calls. Further factual/model-contract work is
a separate repair milestone; these results do not declare release readiness.
