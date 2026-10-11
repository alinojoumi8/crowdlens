# Saved claim reviews

On a saved report, open a proposal from **Saved proposals for this section**,
then **Record your review**. Proposals need a sealed claim ledger and retained
original excerpts. Creating a new proposal is a separate generation action;
opening, saving and exporting reviews makes no generation requests.

Enter a consistent reviewer name, open the review, compare every claim with its
sources, and record only judgments actually made. Support, attribution, citation
support, reference facts, omissions and conflict handling can remain unassessed.
Ratings require a reason/source reference. Optional notes are retained. The
timer starts explicitly and pauses on window blur, page hiding and save; missing
time remains null. It measures browser activity, not verified human effort.

Each save appends a version; concurrent edits cannot overwrite a newer save.
Reopen a saved reviewer to edit their latest version. Other reviewers remain
separate and differing labels are displayed together. Reviewer names/roles are
self-reported, not authenticated identities or professional sign-off. Reviews
never approve a report, replace AI checks or change sealed proposals/reports.

**Export packet and reviews** downloads the frozen sources/claims, latest JSONL
forms, full version history and rubric assessment in one ZIP. It uses the same
[evaluation rubric](evaluations/evidence-quality-human-review.md). This application
packet is not blinded; it is not a held-out benchmark or proof of model quality.
Unzip it, then validate/import without overwriting previous output:

```bash
backend/.venv/bin/python backend/scripts/score_evidence_quality_reviews.py \
  --packets /path/to/export/reviewer --reviews /path/to/export/reviews.jsonl \
  --output /path/to/new-assessment.json
```

Packets are bound to a content SHA-256. Changed sources or wording cannot inherit
old labels. Storage is `.human-reviews.sqlite3` inside the proposal root; include
that hidden database and its SQLite sidecars in a cold backup of the whole report
root. Do not copy a live database without the documented SQLite procedure.

Offline verification: 853 backend tests, 88 frontend tests and production build
passed. A fictional browser session saved two reviewers/three versions, reopened
in a fresh tab, retained partial values/time, showed disagreement, and downloaded
a ZIP that passed the actual rubric importer. The parent remained byte-identical
and external provider calls stayed zero. Those synthetic labels are test inputs,
not independently collected human reviews.
