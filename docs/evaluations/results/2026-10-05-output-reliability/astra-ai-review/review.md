# Astra AI source review — v6

**Four actual drafts reviewed; one semantic strengthening remains.** Of **25 exact ledger claims**, **24 are supported and 1 is unsupported**; none is labelled ambiguous or conflicting. Attribution and citation support are correct for 24 claims and fail for the same one claim. All **22 frozen material facts** are covered by the complete sections, with no material omissions found.

| Packet | Ledger result | Source-scoped summary |
| --- | --- | --- |
| `packet_0958d6a0b53b` — archive trolley | 6 supported | Supported; allocation, pending quote, no recorded spending and no order stay distinct. |
| `packet_28e1b20f56b8` — projector booking | 6 supported | Supported; pending booking and absence of recorded confirmation/delivery/payment remain qualified. |
| `packet_5b040749d729` — cleanup attendance | 5 supported | Supported; session populations, coordinator exclusions and endorsement limits remain distinct. |
| `packet_a9e0e1172d1a` — glazing sessions | 7 supported; 1 unsupported | Repeats unsupported `claim_06`, despite preserving the other conditions and qualifications. |

## Remaining defect

Elmreach `claim_06` says accessible-bench confirmation is a condition **“that must hold before any group assistance could occur.”** S02 `followup.txt`, p. 1 ¶1, says only that **Sora's group could assist if accessible benches are confirmed**, and that this is possible future assistance, not an existing commitment.

The claim turns a stated conditional possibility into a universal prerequisite. S02 does not say *only if*, nor exclude every other form or circumstance of group assistance. This is unsupported strengthening, not a missing citation. By contrast, S01 explicitly uses **only when** for certified-instructor presence, so the necessary staffing condition in `claim_03` is supported.

The selected-claim summary repeats `claim_06` verbatim, so the defect survives summary construction. `claim_07` remains supported: its conclusion that unsupervised access is not approved and assistance is not committed follows independently from claims_01–05; it does not require claim_06's stronger restriction. Correct inclusion of the original Sora statement elsewhere means this is an added inference error, not a material omission.

## Source and summary checks

The archive section preserves the $510 ceiling versus the $360 pending quote, excluded permanent shelving, no recorded spending and no issued order. It does not infer that no actual purchase ever occurred. The projector section keeps the November 12 proposal pending and bounds delivery/payment absence to the supplied records. Its description of an open clarification is read as unresolved in those records, not proof of no external response. The cleanup section preserves 46 versus 31 public volunteers at different sessions, three separately counted first-session coordinators, unrecorded second-session coordinator attendance and the absence of endorsement.

All complete sections were inspected for material claims outside their ledgers; none were found. The supplied sources are compatible, and the sections disclose their material distinctions. Conflict handling is therefore true for all four sections; it does not certify every inference. Analysis claims were allowed valid premise-source support without direct citations. Bounded statements that the complete sources do not record purchases, signatures or approvals were not treated as claims those events could never have occurred.

All **25 selected summary claim IDs** are valid and their rendered text matches the supplied normalized replacement text. **4/4 normalized spans** match their original target exactly and are in bounds; **4/4 supplied summaries** match those spans plus preserved context. These are text-level checks, not acceptance or runtime findings. `candidate_section_summary` is null and freeform replacements are empty as expected for the supplied selected-claim interface; no separate model-authored summary was required or invented.

The inherited sentence **“An unrelated ventilation check is pending.”** appears **exactly once in 4/4 candidate summaries**, remains outside every replacement, and is unchanged from the original comparison suffix. No duplication or new unrelated source-scoped sentence was found. Its factual truth is outside the eight originals and remains unverified; preservation does not verify ventilation status.

## Provenance, validation and next step

Input was restricted to `/home/ali/Documents/CrowdLens-reviews/2026-10-05-source-review-v6/review-final/reviewer` packet JSONs and blank forms. Four tasks and eight complete fictional originals were read before any candidate prose; 22 material facts and all supplied source hashes were frozen first. No administrator data, run/results, diagnostics, gates, index page or code was inspected. Original comparison text served only as a replacement target. No provider was called and no original was edited, proposal accepted or report published.

Reviewer: `gpt-6-astra-max-source-review-v6`; kind **ai**; model `gpt-6-astra`; effort `max`; reviewed at `2026-10-05T04:38:43.329555+00:00`. `review_seconds` is null in every row. Packet hashes, exact claim coverage, source hashes, immutable reference facts and timezone-bearing provenance were validated. These are source-bounded AI opinions, not human ratings, adjudicated truth or release approval.

Next: address the universal-prerequisite wording in Elmreach claim_06 and its selected-summary use while retaining the accurate possible-assistance qualification. The repeated booking statements and verbose selected-claim summaries are secondary editorial issues; they do not change the source-support findings.

Frozen reference SHA-256: `971ee3c4562e696720cff5c8c9f9a47653ae64204fa879d0d2c0804ac8035891`.

- [Frozen source-first facts](source-first-reference-facts.json)
- [Four complete AI review records](reviews.jsonl)
- [This review](review.md)
