# Actionable summary scope and AI assessment

Policy v14 separates deterministic summary mapping from a model's factual
judgment. A missing unique section-to-summary span produces a blocking
summary_scope_unmapped finding with a next step. It retains the original summary,
does not authorize guessed edits, and does not imply a factual contradiction.
A positive model judgment cannot override that mapping block.

New audits supply a summary_assessment with consistent, contradicted or unverified
outcome, rationale and original evidence IDs. The consistency boolean must agree.
A contradiction requires at least one actual source ID. Uncertainty and adverse
judgments remain blocking, and a structural retry cannot erase an adverse
assessment. These judgments remain fallible AI review, not factual certification.
Raw model responses remain in private diagnostics. The normalized assessment is
sealed in the proposal digest and immutable after generation.

Acceptance independently recomputes scope from the frozen parent and validates a
positive assessment, even if findings have been removed from a digest-consistent
candidate. Earlier policy digest shapes are unchanged. Historical reports,
proposals and human-review ratings are not migrated or rewritten. The UI explains
legacy boolean judgments conservatively and links new assessment evidence,
including retrieved sources not cited in the claim ledger.

Validation covers mapped/unmapped outcomes, missing/malformed assessments,
contradiction references, adverse retry preservation, digest/immutability,
acceptance revalidation and original-report preservation. Frozen corpus inputs
and v1 expectation snapshots remain untouched; the test explicitly records the
v14 fail-closed mapping delta. These reused cases are regression evidence, not a
new holdout or model-quality score. A provider-disabled browser fixture showed
separate scope and unverified findings, unchanged summary and disabled saving.

Full local validation: 1006 backend tests, 104 frontend tests and production build.
Independent AI subagent review exercised the affected backend/UI suites and
verified the retrieved-source link correction. Exact-revision CI, image smoke and
deployment receipts are recorded in Confluence and the private
/home/ali/.local/state/crowdlens/summary-scope-20261014/ directory. No hosted inference
was performed. Source-completeness work remains a separate next item.
