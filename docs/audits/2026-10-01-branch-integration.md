# Remaining branch integration

Date: 2026-10-01

## Scope

Compared fetched local and remote branches with CrowdLens main. Only
`codex/evidence-first-reports` had missing commits: 13 commits adding persisted
source-based drafting proposals, review APIs, and immutable report revisions.
The integration preserves existing CrowdLens branding and dependency fixes.
The source worktree was clean and was left intact.

## Review and fixes

Reviewed proposal admission, source scoping, request budgets, immutable revision
publication/recovery, and the review UI. No blocking code issues were found.
Normalized legacy temporary-directory labels in imported historical documentation
and added the feature guide to the README. Recorded historical measurements
remain unchanged.

## Verification

- 347 backend tests, 12 frontend unit tests, and 16 component tests passed.
- Production frontend build succeeded.
- A copied source tree without `.env` files or provider credentials passed all
  347 backend tests using the installed Python 3.11 dependency environment.
- Root and frontend dependency audits reported zero vulnerabilities.
- Compose configuration and whitespace/conflict checks passed.
- Synthetic browser flow verified one accepted proposal and one blocked proposal,
  exactly one immutable child revision remaining `needs_review`, and unchanged
  parent artifact hashes. Real provider HTTP calls were disabled by the harness.
- Documentation scanned for legacy branding; none remains in tracked documents.

Synthetic checks establish workflow mechanics, not factual or forecast quality.
GitHub CI is required before merging this integration into main.
