# CrowdLens report reliability — 2026-10-03

Application candidate: `7f4d68e2d6b1184d299aa9ad81be95aeea8b446f` on the local
`codex/crowdlens-control-recovery` integration branch. Runtime source fingerprint:
`311188690e104b88e865e180fda0367c7616ea4c69ea0c07a3247ad00bb64e20`.
The later reporting commit changes documentation/evidence only. The four scoped
[tasks](../tasks/2026-10-03-report-reliability.md) implement the corrective work
identified by the [previous actual test](2026-10-03-live-cedarbrook.md).

## Implemented boundaries

1. Proposal diagnostics retain actual completion text before JSON cleanup/parse,
   parsed JSON when available, exact audit fields and paragraph findings. These
   are private capped snapshots, not full HTTP envelopes. Public review exposes
   precise findings and a digest. Prompts describe the existing typed contracts;
   invalid audit coverage, boolean types and inconsistent paragraph/claim kinds
   still block. Cancellation, ownership and immutable acceptance guards remain.
2. New reports freeze original graph/version source excerpts and actual action
   rows with their origins, references and digests. Graph paraphrases and seeded
   inputs cannot pass as exact original/model quotations. The saved forecast is
   frozen before prose and supplies the table and UI, including resume/regeneration.
   Percentage checks reject unsupported values outside the frozen forecast block.
   Semantic phrasing remains outside that mechanical guard. Thin runs remain thin.
3. Activity counts distinguish unique posts, model actions, initial inputs,
   scheduled posts and event markers. No-op actions are counted as model actions
   but excluded from expressed-support forecast synthesis. The worker and UI use
   effective duration/round bounds and selected platforms; legacy aliases remain
   explicitly labelled. Idle, Starting, Running and terminal states are preserved
   across reads/reload. Home history uses the configured/fallback root-report
   store and isolates unreadable records; later revisions cannot displace roots.
   The writer requires nonempty completed prose after cleanup within its bounded
   ReACT loop, retaining unfinished process notes as attempts. Memory-off help
   and graph hints do not claim live updates
   or measured accuracy; diagnostic activity scores disclose their heuristics.
4. Fresh generation checks the planned summary and each section. A blocking
   quotation/percentage passage gets at most one ordinary counted correction,
   retaining active-attempt before/after text and findings in `agent_log.jsonl`.
   The unchanged guard validates its output and the assembled report. Invalid,
   empty or late responses cannot make a successful report. Existing summaries
   are not automatically repaired on Resume; late text rejected by Stop is not
   appended to the report log. This is not independent semantic adjudication.

## Regression and independent review

`UV_PYTHON=3.11 npm run check` passes **563 backend + 12 Node + 51 component
tests** and the production frontend build. Runtime versions: Python 3.11.15,
Node 24.21.0. Diff whitespace checks pass. Fail-first checks cover proposal audit
and paragraph diagnostics, false activity, round bounds, status restoration,
unsupported prompt examples, terminal report headers, the correction boundary,
configured/fallback root history with bad/legacy metadata, and cleaned final-answer
completion. Static independent review identified two edge cases; both are fixed.
The captured nine-quotation real-model fixture stays blocked after the repairs.
Independent read-only AI review found no blocking issue in the final changes.
It confirmed unchanged guards and bounded correction; it does not certify prose
entailment, omissions, factual accuracy or calibration.

## Preserved intermediate attempts

Five separate candidate workflows stopped with **87 completed physical model
requests** (11 + 9 + 21 + 22 + 24), zero in-flight/delivery-unknown attempts. They
identified false memory/accuracy copy and two genuine quote-validation failures.
A later partial journey accepted/reloaded an immutable child but failed history
reopen; it also retained an unfinished first-section process note. Those defects
were reproduced and repaired before the final frozen candidate. That root also
misattributed a no-op participant as the opposing-action author, despite the
saved actual-action packet. Mechanical scores of 95/100 did not establish
semantic validity. The first blocked root retained nine findings; the next
retained four altered
response/unsupported-label quotations. Neither supplied a successful fresh
acceptance result. Original report files and the 50-file historical baseline
remain preserved; their manifests and retained actual ledgers are separate from
any final-candidate success. No billing dollar amount is known.

## Fresh visible-browser result

**All four scoped tasks are complete locally.** The real visible-browser journey
completed upload → graph → preparation → OASIS → root report → source proposal →
local test revision acceptance → reload → Home simulation history → root report →
saved child. Candidate, input, effective settings and frontend stayed unchanged.
The final report is [open locally for review](http://127.0.0.1:18780/report/report_3d12d343d6fa4c5d86998d8d88ea042a).

| Boundary | Observed result |
| --- | --- |
| Original packet | Fictional Cedarbrook Markdown, 1,471 bytes; source SHA-256 `1d79d4a96e4af613f81a1a9195a277ee15753a154d6e2daf48ddd7fae4aaf48b`; requirement SHA-256 `46b6a2f9ce9ff202bd0a295a71ec731d233e3298da5faea59493f9dd23a3bd4f`. |
| Graph and setup | Project `proj_cab56063dd57`, graph `a4f570c2-385a-4c5a-a441-acf564cf4fa9`: 5 nodes / 8 edges; Maya, Leo, Priya and Daniel generated. |
| Runtime | Simulation `sim_2757a283087d`: Twitter only, seed 42, memory Off, one active agent per round, two effective rounds; requested legacy cap 72 is explicit. |
| OASIS | Completed in about 20 seconds; two Maya model posts, 4 initial + 4 scheduled posts + 4 event markers; 10 unique posts, 14 activity entries. SQLite: 10 posts / 14 traces including 4 signup rows. One Start HTTP request. |
| Reload | Idle before Start, Running after Start, and Completed after the worker finished survived reload without another Start. |
| Root report | `report_7b90d18cdb75`, three completed sections in 63.53 seconds. Initial/final forecast probabilities remain 23.4 / 51.6 / 25.0; two model actions / one active agent. These are uncalibrated heuristic estimates. |
| Correction | Source and simulated-discussion sections each used one counted correction; their 6 and 9 quotation findings, before/after passages and accepted guard results remain retained. Final mechanical findings are empty. |
| Proposal | `proposal_a960d285e17d4a339892b7647869c301`: three real drafting calls; Ready → Accepted. Eight claims, one original excerpt, `premise_unverified` review finding, no summary change. Private planning/drafting/audit completion and parsed snapshots remain intact. |
| Child | `report_3d12d343d6fa4c5d86998d8d88ea042a`, immutable **Needs review**; all nine parent files, forecast, summary and unselected sections unchanged. Reload and UI history reopen pass. |
| Accounting | Workflow `wf_e39ea20ed1fd4f0aaff7c8f27c52a32a` stopped at **26/90 responses**, 60-minute allowance, zero in-flight/unknown calls. Together with the five partial candidates: **113 responses**. Tokens are retained; measured monetary cost is unknown. |

MiniMax-M3 used the configured `https://api.minimax.io/anthropic` endpoint with
transport retries disabled. The proposal usage adapter labels its protocol
`anthropic`; the actual workflow/provider endpoint is MiniMax. Embeddings used
the existing local `nomic-embed-text`; no model was pulled. New data roots,
control database and Neo4j volume started empty. Earlier owned temporary services
are stopped; the final loopback runtime remains available with generation stopped.

The root incorrectly says Round 1 contains no model action, although
`twitter:trace:11` is Maya's Round 1 post. Its later paragraph also describes that
post as the first model action. This contradiction remains inherited in the
unselected section. The source proposal flags an unverified premise in its
conditional-symmetry analysis. A mechanical score of 100 does not resolve either
issue. Acceptance verifies persistence and review workflow, not prose truth.

[Selected receipts, check logs, hashes and screenshots](evidence/2026-10-03-report-reliability/README.md)
record the exact candidate. Raw private completion snapshots, credentials,
wrappers and control databases are excluded from the committed bundle. The
50-file historical baseline and retained blocked/partial report manifests are
unchanged. README, roadmap, capability manifest, ECC/browser plans and task
checklist now point to this result without transferring historical release claims.

## Next boundary

First reproduce the retained Round 1 contradiction and unverified-premise case
as independently labelled regressions. Then measure claim support, incorrect
attribution, omissions and reviewer time on
approved held-out packets with independent labels. One fictional accepted journey
cannot establish cross-packet reliability, model quality, forecast accuracy or
release readiness. Broader inputs/providers, memory/ensemble recovery and browser
accessibility/responsiveness remain separate verification work. Exact-candidate
remote CI, image/clean-install checks and deployment reconciliation require the
separate release task; previous candidate results do not transfer. This work
makes no push, main merge, deployment, generation-model download or publication.
