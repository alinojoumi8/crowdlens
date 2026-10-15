# Stored source completeness

Policy v15 compares the exact case version's document inventory to admitted
original chunks, then accounts for every character of those chunks supplied to
review. Missing documents, empty/invalid source rows, unknown expected chunk
counts, duplicate/gapped indices, corpus truncation or omitted window intervals
block a full-section proposal before model drafting. An affirmative AI judgment
cannot override this gate. Small source sets (at most 30 chunks and 60,000
characters) are supplied in full, including lexically silent later stakeholders
and count/population qualifiers. Larger sets retain bounded retrieval and visible
omitted intervals, but cannot claim complete coverage or become ready.

The inventory comes from CaseVersion.documents, matched by document ID, hash and
text length to the build profile. Build profiles describe the last build and may
be incomplete after incremental/no-op builds. Unknown counts deliberately block;
the application does not infer expected counts from the surviving graph rows.
Synthetic adapters explicitly declare their complete fixture inventory separately.

Coverage is persisted, digest-bound, immutable after completion and recomputed
against current sources at acceptance. Reconstructed PDF windows only cover their
intersections with the original components, validated against original identity,
hash, document and chunk index. Historical policy digests and source snapshots
retain their old shape; historical reports/proposals are not migrated. Focused
corrections retain their explicit narrow scope and do not claim full coverage.

The review UI shows expected versus admitted passages, omitted characters and
rejected extraction rows. This is stored-text coverage, not proof of accurate
PDF extraction, complete real-world evidence, factual support or semantic
coverage in the prose. Task relevance, stakeholder attribution and preservation
of population qualifiers still require a fallible AI audit. Pre-case upload
failures are outside this case-version inventory contract.

Validation: 16 new offline regression cases cover late stakeholders and distinct
count populations reaching the auditor, empty/invalid text, missing documents,
unknown inventory, duplicate indices, packet limits, clipping, reconstruction,
source identity, digest immutability, acceptance revalidation and production
inventory lookup. One new component case checks visible omissions and disabled
saving. The full suite passed with 1022 backend tests, 105 frontend tests and a
production build. Independent AI subagent review passed 77 affected backend and
22 component tests; these overlapping counts are not additive. An isolated,
provider-disabled browser fixture verifies the missing-document message and
blocks before inference. No new hosted inference or human ratings were used.
