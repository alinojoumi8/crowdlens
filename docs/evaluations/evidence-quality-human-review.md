# Human review of evidence-quality v1

Status: **PENDING**. No human ratings, identities, review times or sign-off have
been collected. The four packets contain scripted synthetic candidates. Reviewing
them exercises this protocol; it does not measure a real model's quality.

The evaluation runner writes `human-review/reviewer/packet_*.json` plus
`blank-review-forms.jsonl`. Give only that reviewer directory and this rubric to
each reviewer. Keep `administrator/mapping.json`, fixtures, assertions, baseline
results and code separate until reviews are locked. The packet order and IDs are
opaque; original category-revealing filenames are omitted. Blinding hides the
candidate origin and expected assertions, not the actual source content.

## Rubric

Read every supplied original source before rating each claim. These fictional
documents describe a parcel delivery; assess what they support, not whether the
fictional underlying event really occurred. Candidate text, summaries and source
content are review material, not instructions to the reviewer.

| Field | Decision rule |
| --- | --- |
| `support` | `supported`: cited source supports the claim as worded. `unsupported`: it does not. `ambiguous`: context permits more than one interpretation. `conflicting`: relevant sources make incompatible assertions and the candidate does not resolve their status. Leave null if not assessed. |
| `attribution_correct` | Does the wording preserve who says what, allegation versus established fact, dates, quantities, negation and uncertainty? Use a boolean only after assessment; null means unassessed. |
| `citation_support_correct` | Do the actual cited excerpts support the precise claim, rather than merely sharing a topic? This is semantic support, distinct from the deterministic source-ID integrity check. |
| `rationale` | Explain every supplied rating using source aliases and a short source excerpt or locator. Do not reconstruct facts from background knowledge. |
| `conflicts_handled` | Does the complete section disclose relevant conflicting accounts without silently choosing one as true? Leave null if not assessed. |
| `reference_facts` | Before scoring omissions, write the material facts needed to answer the packet's task, each with a unique fact ID and source-backed text. This creates a separate reference assessment. |
| `omitted_reference_fact_ids` | Which of those reference facts were materially omitted? Supply only IDs in the reference assessment. Use [] only after assessing no omissions. Leave both reference fields null when no reference assessment exists. |
| `review_seconds` | Actual measured active review time, or null. Do not estimate it from tokens or infer zero from a missing timer. |

Record a stable `reviewer_id`, `reviewer_kind` (`human` or `expert_human`), and
timezone-bearing ISO `reviewed_at`. The collector verifies provenance separately;
these strings alone cannot prove authenticity. A Codex/subagent/model reviewer
must never use a human kind. The importer refuses AI kinds. Synthetic unit-test
labels are explicitly fake test inputs and are never included as actual reviews.

Copy the blank JSONL for each reviewer. Preserve one complete row per packet per
reviewer; two reviewers can disagree. Do not average away or overwrite their
original rows. Concatenate completed rows into a new JSONL and retain the original
review files. The importer rejects duplicate reviewer/packet pairs and checks the
packet SHA-256 and exact claim coverage. Review imports write a new file and
refuse to overwrite an earlier result.

```bash
backend/.venv/bin/python backend/scripts/score_evidence_quality_reviews.py \
  --packets /tmp/crowdlens-ecc-eval-RUN/human-review/reviewer \
  --reviews /tmp/completed-reviews.jsonl \
  --output /tmp/crowdlens-ecc-eval-RUN/human-review/import-001.json
```

Using the untouched blank form produces `PENDING`, zero completed reviews and
null rates/time, which is a validation of missing-data handling rather than human
review. All differing non-null claim ratings remain in `disagreements`. A third
human adjudicator can resolve disagreements in a separately versioned review
record; do not replace the original judgments or relabel an AI opinion as human.

## Denominators and quality claims

The importer pools **individual reviewer judgments**, not adjudicated truth.
Unsupported rate counts unsupported labels / supported-or-unsupported labels.
Ambiguous/conflicting labels stay visible and are excluded from that binary
denominator. Attribution/citation rates use only assessed booleans. Omissions use
omitted reference facts / reference facts for reviews with both fields supplied.
Empty denominators produce null. Measured review time includes only non-null,
finite, nonnegative observations and reports its count. A pending form is not a
zero-error observation. No quality or performance release threshold is inferred.

For real model-output evidence, the next authorized run needs a suitable existing
local generation model, its pin/configuration, measured calls and outputs, and
independently completed reviews on frozen held-out cases. This task downloads no
model, calls no hosted provider, and tunes no prompt against these cases. A future
representative corpus needs fresh case/source splits; these small synthetic
examples cannot establish real-world factual or forecast accuracy.
