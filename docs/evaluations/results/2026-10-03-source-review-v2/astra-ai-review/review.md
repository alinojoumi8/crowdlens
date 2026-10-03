# Independent AI source-and-claim review

**Status: complete AI review; not human review, adjudication, acceptance or release evidence.**

Reviewer: `gpt-6-astra-max-source-review-v2` · model: `gpt-6-astra` · reasoning effort: `max` · reviewed at: `2026-10-03T23:00:38.035957+00:00`. All four rows use `reviewer_kind: ai` and `review_seconds: null`; no human timing was measured or inferred.

All four packets and all eight supplied original fictional documents were reviewed. All 19 exact ledger claim IDs were assessed. The labels are 17 supported, 1 unsupported and 1 ambiguous, with no individual claim labelled conflicting. Attribution and precise citation support are each true for 17 claims and false for 2. These are descriptive judgments by one AI reviewer, not accuracy estimates or adjudicated error rates.

The main weakness is source coverage: every section uses S01 and omits material S02 content. Ten of 28 material reference facts frozen before candidate review are absent from the complete sections. The library section leaves out the second attendance account; the ramp section leaves out all named stakeholder positions. All four authored comparison summaries remain the same generic sentence. Raw proposed replacements, where supplied, were reviewed separately and were not applied.

## Review boundary and source-first record

Inputs were limited to the reviewer packet JSON files, blank review forms, and the permitted rubric at `docs/evaluations/evidence-quality-human-review.md`. The rubric's opening historical v1/scripted/parcel statements were not treated as descriptions of these v2 packets. No administrator mapping, raw run records, diagnostics, corpus fixtures, expected assertions, prior outcome summaries, application code, external factual sources or browser state was consulted. No provider was called, proposal accepted, human importer changed or AI form submitted as human.

All tasks and original source texts were read before any candidate/claim content was displayed. Structural keys/types and blank claim IDs were inspected first solely to isolate sources. Twenty-eight source-only material facts were written, made read-only and frozen at `2026-10-03T22:51:57.106400+00:00` before candidate review. The file was not revised after that point.

Frozen file: [source-first-reference-facts.json](source-first-reference-facts.json). SHA-256: `acbe2833cd333bec6dd74ce98a3ca24f1cba8e3989ddbba08dcedad505a04baf`.

Every original packet hash matches the untouched value in its blank form. Each output row copies that form, preserves its hash and exact claim IDs, includes the frozen reference facts, and adds explicitly labelled AI-only whole-draft/summary/proposal assessments. [reviews.jsonl](reviews.jsonl) is an AI review artifact, not a file for the human-only importer.

Citation judgments assess semantic support, not merely whether an ID exists. Analysis claims can be supported through their explicit premise-to-source chains without direct citations. A flawed compound premise does not invalidate an inference independently supported by other cited premises; those cases are explained individually. “Supported” means supported by the fictional supplied text, not independently verified in the world.

Omission IDs evaluate the complete candidate section, not just its ledger. Authored summaries and raw replacement text are separate surfaces and do not count as applied repairs. A fact partly or inferentially preserved can count as covered when its material meaning survives. False conflict judgments below include failure to disclose differing accounts or stakeholder cautions; they do not assert that every omitted pair is logically contradictory.

## Findings by packet

| Packet | Ledger judgments | Material facts omitted from section | Conflicts handled |
| --- | --- | --- | --- |
| `packet_0cb718ce2d34` — shuttle | 4 supported; 1 unsupported | 3 of 7 | Yes; sources compatible |
| `packet_899779dccb4a` — library | 3 supported; 1 ambiguous | 2 of 6 | No; second account/status absent |
| `packet_dd4cc5e995cb` — ramp | 5 supported | 3 of 8 | No; differing positions/cautions absent |
| `packet_e7c7c3cf0192` — garden | 5 supported | 2 of 7 | Yes; supersession retained |

### Shuttle pilot — `packet_0cb718ce2d34`

**Exact claim review.**

| Claim | Support | Attribution | Citation support | Rationale |
| --- | --- | --- | --- | --- |
| `claim_01` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) says Rosa Lin 'could support a six-week trial if wheelchair boarding is demonstrated.' The claim preserves the speaker, six-week duration, possible support and the accessibility condition; it does not turn the condition into an unconditional endorsement. |
| `claim_02` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) says Amir West requires retained evening service and 'does not state support or opposition.' The claim keeps that requirement separate from a position on the trial. |
| `claim_03` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) attributes both 'no permanent route decision has been taken' and 'the trial has not started' to planner Elena Frost. Both negatives and their attribution are preserved. |
| `claim_04` | unsupported | Not preserved | Not precise | S01 (D01, p. 1, para. 1) supports the fictional Northmere workshop description and the absence of recorded blanket support for permanence. However, neither S01 nor S02, nor their supplied document metadata, identifies a file named meeting.txt. The exact compound claim therefore adds unsupported documentary provenance. Attribution and citation support are false for that filename clause; this does not mean the workshop or the limited-support conclusion is unsupported. |
| `claim_05` | supported | Correct | Correct | The material inference follows from claim_01 -> S01 (Rosa's possible support is conditional and for a six-week trial), claim_02 -> S01 (Amir states a requirement without support or opposition), and claim_03 -> S01 (Elena reports no permanent decision and no start), all at D01, p. 1, para. 1. These premises support saying that universal support for permanence is not established. Direct citations are not necessary here because those premise-source chains are explicit. Although claim_04 also contains an unsupported filename, this conclusion does not depend on that filename. 'Conditional endorsement' is accepted here as shorthand for the explicitly qualified possible support in the same section, not as proof of a present commitment; the raw replacement's stronger wording is discussed separately. The proposed old_text supplies the quoted prior sentence, but no independently authenticated earlier report is provided. |

**Whole draft.** All material factual propositions in the section are represented in the five ledger entries. The ungrounded meeting.txt attribution is already inside claim_04, rather than a separate unledgered claim. The complete draft otherwise retains the named speakers' positions; its analysis must be read with Rosa's 'could support' qualification.

**Omissions against the frozen source-only reference.** The complete section omits S02's scheduled council discussion on 18 November, the explicit absence of a vote and the absence of ridership/cost figures. These are material proposal-status and evidence boundaries. The omitted facts also remain absent from the raw proposed replacements.

- `P0CB-F05`: The council will discuss a proposed six-week shuttle trial on 18 November. (S02 / D02 p. 1, para. 1).
- `P0CB-F06`: No vote has been held on the proposed trial. (S02 / D02 p. 1, para. 1).
- `P0CB-F07`: No ridership or cost figures are available. (S02 / D02 p. 1, para. 1).

**Conflicts handled: true.** The two original sources are compatible. The section preserves Rosa's conditional possible support, Amir's uncommitted requirement and Elena's status statements. True records that no incompatible account was silently selected; it does not imply complete source coverage.

**Authored comparison summary.** `The fictional source records require careful review.` This remains generic and provides no task-specific material facts. It is assessed as authored, independently of proposed edits.

**Raw proposed replacements — unapplied.**

- Proposal 1 (`0:48`, claim IDs `claim_04`): The proposed negative statement about absence of recorded blanket support for permanence is supported by S01 (D01, p. 1, para. 1), with compatible pending-proposal status in S02 (D02, p. 1, para. 1). It drops the unsupported filename from claim_04's text, but remains an unapplied proposal and adds none of the omitted S02 facts. Against the supplied 52-character authored summary, the range is within bounds and the sliced text does not match the declared old_text.
- Proposal 2 (`48:98`, claim IDs `claim_05`): The central inference against universal support for permanence is supported by S01 (D01, p. 1, para. 1). However, standalone 'Rosa Lin conditionally endorses' is stronger than the source's 'could support ... if'; it may imply a present conditional commitment rather than willingness. Its use of 'only' should be confined to the recorded proposal, not Rosa's possible views on other proposals. It does not restore any S02 facts. The claimed prior sentence appears as the other proposed edit's old_text, not as an independently supplied prior report. Against the supplied 52-character authored summary, the range is out of bounds and the sliced text does not match the declared old_text.

These are packet-level comparisons under a zero-based half-open character-range interpretation. No supplied target makes the proposal both in bounds and an exact old-text match. An unseen original target or different application contract cannot be evaluated from this packet; no runtime conclusion or repaired output is inferred.

### Library attendance — `packet_899779dccb4a`

**Exact claim review.**

| Claim | Support | Attribution | Citation support | Rationale |
| --- | --- | --- | --- | --- |
| `claim_01` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) is a visitor register signed by coordinator Nia Cole and states 18 Saturday workshop visitors, two later-hours requests and no repeat-visitor identifier. The claim preserves the visitor population and all three limitations. It does not assert that the register counts staff and volunteers. |
| `claim_02` | ambiguous | Not preserved | Not precise | S01 (D01, p. 1, para. 1) records 18 visitors, while S02 (D02, p. 1, para. 1) reports Finn Reed's 23 attendees including volunteers and staff without separating visitors. Calling the register's count '18 attendees' could mean its 18 visitor attendees, but can also be read as total event attendance. The exact claim drops the material visitor-only population qualification, so attribution fidelity and precise citation support are false. Nia's signatory identity, the two requests and the absence of an identifier are otherwise supported. These counts are not necessarily incompatible because their population definitions differ; I do not resolve them or label the event total as 18 or 23. |
| `claim_03` | supported | Correct | Correct | Claims_01 and _02 point to S01 (D01, p. 1, para. 1): one Saturday visitor count, only two requests and no repeat-visitor identifier. Inspection of the complete S01 confirms no prior-period figure, and S02 (D02, p. 1, para. 1) also explicitly supplies no comparison-week figure. The inference that doubling and universal later-hours demand are not established is valid through claim_01 -> S01 despite claim_02's population ambiguity; there is no need for a direct citation on the analysis itself. Lack of evidence for those propositions is not proof that attendance did not double. An independent before-section is absent, so I assess the stated proposition's evidential support rather than authenticating that an earlier author made it. |
| `claim_04` | supported | Correct | Correct | The complete S01 (D01, p. 1, para. 1) has no comparison-period count or ratio establishing doubling and records two later-hours requests among 18 visitors. The wording is appropriately scoped to what the register establishes and does not treat attendance as equivalent to demand. This valid S01 claim does not compensate for omitting S02 from the section. |

**Whole draft.** No wholly separate factual proposition outside the ledger was found. The section's second paragraph adds 'According to Nia Cole' framing, whereas claim_02 identifies her as signatory; this is acceptable only as attribution to the signed register, not as evidence of a separate spoken or written personal account. Both versions retain the ambiguous '18 attendees' wording. The section supplies no second attendance account or reconciliation status.

**Omissions against the frozen source-only reference.** The second attendance account and its non-correction/non-withdrawal status are wholly omitted. The absence of a comparison figure is substantively covered by the section's analysis, so P899-F06 is not marked omitted even though S02 is never cited.

- `P899-F04`: Volunteer Finn Reed reports counting 23 attendees including volunteers and staff, without distinguishing visitors from staff. (S02 / D02 p. 1, para. 1).
- `P899-F05`: Finn Reed's email does not correct or withdraw the signed visitor register. (S02 / D02 p. 1, para. 1).

**Conflicts handled: false.** The section presents only the signed register. It does not disclose Finn Reed's separate count of 23 including volunteers/staff or the email's express statement that it does not correct or withdraw the visitor register (S02, D02, p. 1, para. 1). It therefore fails the task's requirement to retain the unresolved discrepancy. The sources use different population definitions, so this is a missing-account/status failure, not a reviewer finding that the two numbers necessarily contradict each other.

**Authored comparison summary.** `The fictional source records require careful review.` This remains generic and provides no task-specific material facts. It is assessed as authored, independently of proposed edits.

**Raw proposed replacements.** None supplied. The generic authored summary therefore has no proposed replacement to assess.

### Boat-ramp proposal — `packet_dd4cc5e995cb`

**Exact claim review.**

| Claim | Support | Attribution | Citation support | Rationale |
| --- | --- | --- | --- | --- |
| `claim_01` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) gives 'an early estimate' of 'approximately $18,000, excluding permits and maintenance.' The claim retains the early/approximate status and both exclusions without presenting a final cost. |
| `claim_02` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) states that the design is provisional. The claim attributes that status to the brief and makes no assertion of final design approval. |
| `claim_03` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) says no queue timing study, user survey or funding approval is included. The claim preserves the limited documentary assertion; it does not assert that no such material could exist elsewhere. |
| `claim_04` | supported | Correct | Correct | The chain claim_01 -> S01 supplies the early, approximate estimate and exclusions; claim_02 -> S01 supplies the provisional design (D01, p. 1, para. 1). These premises support the inference that the supplied estimate does not establish a final cost. The lack of a direct citation on the analysis is acceptable because the cited premise chain is valid. |
| `claim_05` | supported | Correct | Correct | Claim_03 -> S01 (D01, p. 1, para. 1) establishes that the brief supplies neither queue measurements nor a user survey; the complete brief provides no other evidence establishing queue elimination or full public support. The analysis correctly says those propositions are unsupported rather than disproved. The premise-source chain is adequate without a direct analysis citation. S02 (D02, p. 1, para. 1) also records an unmeasured expectation, a concern/non-endorsement and an assessment prerequisite, but the draft omits these material positions. |

**Whole draft.** The complete section's substantive propositions are covered by its five ledger entries. No additional unledgered factual claim was found. All stated claims are supported, yet the section fails the attribution-of-concerns portion of the task through omission.

**Omissions against the frozen source-only reference.** All three attributed S02 positions are materially omitted. The section covers the S01 estimate, provisional status and unavailable studies/approval, but its generic lack-of-evidence analysis cannot substitute for the omitted named positions. The proposed summary replacement also contains only S01 material.

- `PDD4-F06`: Boater Lena Orr expects easier launching but gives no measured time saving. (S02 / D02 p. 1, para. 1).
- `PDD4-F07`: Angler Theo Vale is concerned about shoreline access and has not endorsed the design. (S02 / D02 p. 1, para. 1).
- `PDD4-F08`: Engineer Mira North requests a site assessment before recommending construction. (S02 / D02 p. 1, para. 1).

**Conflicts handled: false.** The draft omits all S02 stakeholder positions: Lena's unmeasured expectation, Theo's shoreline-access concern and non-endorsement, and Mira's prerequisite site assessment (D02, p. 1, para. 1). These positions can coexist, so false denotes failure to disclose the material differing positions/cautions, not a finding of logically incompatible accounts. Saying full support is unsupported does not preserve who raised which concern.

**Authored comparison summary.** `The fictional source records require careful review.` This remains generic and provides no task-specific material facts. It is assessed as authored, independently of proposed edits.

**Raw proposed replacements — unapplied.**

- Proposal 1 (`0:75`, claim IDs `claim_01`, `claim_02`, `claim_03`): The proposed text accurately preserves S01's approximate $18,000 estimate, exclusions, provisional design and absent timing study/survey/funding approval (D01, p. 1, para. 1). It adds substance to the generic summary but omits every S02 stakeholder position. It has not been applied. Against the supplied 52-character authored summary, the range is out of bounds and the sliced text matches the declared old_text.

These are packet-level comparisons under a zero-based half-open character-range interpretation. No supplied target makes the proposal both in bounds and an exact old-text match. An unseen original target or different application contract cannot be evaluated from this packet; no runtime conclusion or repaired output is inferred.

### Garden trial decision — `packet_e7c7c3cf0192`

**Exact claim review.**

| Claim | Support | Attribution | Citation support | Rationale |
| --- | --- | --- | --- | --- |
| `claim_01` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) identifies final version 2 as superseding the version-1 draft and approves a one-term movable-container trial at Bracken School. The claim preserves both operative-version status and limited trial scope. |
| `claim_02` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) states an allocation ceiling of $2,400. The claim presents it as a ceiling rather than an expenditure total; S02 (D02, p. 1, para. 1) expressly confirms that distinction. |
| `claim_03` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) expressly excludes permanent ground works from the approval. The claim accurately describes the permission boundary rather than claiming any physical works occurred. |
| `claim_04` | supported | Correct | Correct | S01 (D01, p. 1, para. 1) states that no expenditure has yet been recorded. The claim retains the important recorded-information qualifier and does not assert independently proven zero spending. |
| `claim_05` | supported | Correct | Correct | Claims_01 through _04 each cite S01 (D01, p. 1, para. 1) and together establish the one-term movable-container scope, $2,400 ceiling, exclusion of permanent works, no recorded expenditure and supersession. The analysis accurately separates these concepts through valid premise-source chains despite having no direct citation. It is incomplete about the linked procurement status in S02, but that omission does not make these stated propositions false. |

**Whole draft.** All material factual propositions in the section are covered by its five ledger entries. No additional unledgered factual claim was found. The section accurately preserves supersession, scope and recorded-spending qualifiers while omitting the current supplier/ordering status.

**Omissions against the frozen source-only reference.** S02's proposed $1,950 supplier quotation awaiting approval and absence of a purchase order are materially omitted. These clarify that trial approval and an allocation ceiling do not amount to supplier approval or a procurement commitment. The section already distinguishes the ceiling from recorded spending, so PE7C-F03 is not marked omitted.

- `PE7C-F06`: A proposed supplier quotation of $1,950 is awaiting approval. (S02 / D02 p. 1, para. 1).
- `PE7C-F07`: No purchase order has been issued. (S02 / D02 p. 1, para. 1).

**Conflicts handled: true.** S01 expressly gives final version 2 priority over the earlier draft, and the section preserves that status while separating approval, allocation and recorded spending. S02 is compatible, not a competing operative decision. True does not excuse its omitted pending-quotation and purchase-order facts, and the actual earlier draft is not independently supplied.

**Authored comparison summary.** `The fictional source records require careful review.` This remains generic and provides no task-specific material facts. It is assessed as authored, independently of proposed edits.

**Raw proposed replacements — unapplied.**

- Proposal 1 (`0:1`, claim IDs `claim_01`, `claim_02`, `claim_03`, `claim_04`, `claim_05`): The proposed text preserves S01's operative trial scope, allocation ceiling, exclusion of permanent works, no recorded spending and superseded earlier draft (D01, p. 1, para. 1). In context, 'no permanent ground works' describes the decision's permission boundary, not proof about physical works. It omits the pending $1,950 quotation and lack of a purchase order in S02. It has not been applied. Against the supplied 52-character authored summary, the range is within bounds and the sliced text does not match the declared old_text.

These are packet-level comparisons under a zero-based half-open character-range interpretation. No supplied target makes the proposal both in bounds and an exact old-text match. An unseen original target or different application contract cannot be evaluated from this packet; no runtime conclusion or repaired output is inferred.

## Prioritized next steps

1. Address the missing second-source evidence before treating these drafts as complete. Preserve both library counts with their distinct populations and unresolved correction status; restore the three attributed ramp positions; include the shuttle notice's decision/evidence limits and the garden procurement status. Review the resulting section against all frozen source facts, not only the existing ledger.
2. Ground the shuttle's documentary provenance and preserve the library's visitor-only denominator. The packet does not support the filename `meeting.txt`; “18 attendees” loses a material distinction. Retain Rosa's “could support” modality in standalone text instead of assuming a current commitment.
3. Review authored summaries and raw proposals independently. Each supplied summary is generic. If the supplied summary is the intended edit target, none of the four proposed ranges is both valid and an exact match for old_text; establish the actual frozen target/offset contract before any future application. This review did not diagnose the runtime or create a corrected report.
4. Keep these AI judgments separate from human review and preserve them alongside the untouched packets and blanks. Any later disagreement or adjudication should be a new record. Broader quality conclusions would require independent review on fresh representative material; this small fictional set and one AI opinion cannot establish real-world performance.

## Limits and artifacts

The source texts and packet metadata are the complete evidence boundary. No underlying real events, omitted earlier report, actual version-1 garden draft, intended original edit target, application behavior or candidate origin was independently verified. Generic before/prior-section propositions were assessed for evidential support, not authenticated as historical statements by an earlier author. Materiality and borderline wording judgments may differ across reviewers; the library attendee wording and Rosa's standalone endorsement wording are explicitly uncertain rather than resolved by assumption.

No separate material factual claim beyond the ledger was found in any complete section. The library prose/ledger attribution difference is recorded explicitly. The four candidate summaries and the raw proposals, where supplied, were inspected, but no candidate was rewritten, applied, accepted or published.

- [Frozen source-first reference facts](source-first-reference-facts.json): 4 packets, 28 facts, unchanged after freezing.
- [Complete AI reviews](reviews.jsonl): 4 rows, 19 exact claim judgments, original packet hashes preserved, AI provenance and null review time.
- [This review and next steps](review.md): whole-draft, omission, conflict, authored-summary and unapplied-proposal findings.
