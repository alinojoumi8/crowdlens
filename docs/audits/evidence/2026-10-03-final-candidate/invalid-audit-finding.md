# Real proposal audit contract block

The fresh run used frozen candidate `1f61571` and the actual uploaded fictional
source. Three model-backed proposals remained blocked:

| Proposal | Section | Physical MiniMax-M3 calls | Blocking finding |
| --- | --- | ---: | --- |
| `proposal_41906b440b3d49758794e2ea69afb196` | Source facts | 3: ledger, prose, audit | `invalid_audit` |
| `proposal_20eda4b6140f4a2b8541e828165301de` | Source facts, explicit New proposal | 2: ledger, prose | `paragraph_kind_mismatch`, paragraphs 0 and 7; stopped before audit |
| `proposal_58c0cb1b68774a998250e844ae64701a` | Uncertainties, separately selected | 3: ledger, prose, audit | `invalid_audit`; also five nonblocking `premise_unverified` warnings |

The UI shows Changes required and disables Save as new revision. These are
retained safely blocked real-model outcomes, not accepted drafts. The workflow
stopped at 38/45 requests, with one epoch, zero in flight, zero unknown usage,
and no accepted child. The three-section root remains byte-identical.

Read-only tracing confirms `audit_findings` enforces the response structure,
exact target coverage, boolean summary consistency and valid finding targets/claim
IDs. The `invalid_audit` code is generic; the raw returned audit JSON was not
persisted, so the exact offending field and any semantic reason cannot be
recovered from current artifacts. Each blocked proposal retains sources,
ledger, before/after, model usage and findings. A new model call would not
reconstruct the original response. Persisting raw audit output and precise
schema diagnostics remains a verification gap.

The explicit retry and separate section selection occurred visibly under the
existing authorization and unchanged candidate. No validator or source data was
changed, no parent report regenerated and no budget reset. All three attempts
remain available in the source store. Each supplies its own outcome without
overwriting or certifying the others. Full fresh revision acceptance/reopening
was not completed.
