# Beta acceptance evidence closeout — 2026-10-18

> Historical evidence snapshot, preserved on October 29, 2026. Deployment identity, open gates and the next sequence below describe October 18. Later implementation is recorded in the [scope and privacy contract](../beta-scope-and-privacy.md), [authentication](../authentication.md), [workspace ownership](../workspace-ownership.md), [administrator quotas](../administrator-quotas.md), [ingestion hardening](../ingestion-hardening.md), [private staging](../private-staging.md) and [dependency networking](../private-dependency-network.md) records. Use the [current delivery backlog](https://alinojoumi8.atlassian.net/wiki/spaces/CROWDLENS/pages/590020) for current status and remaining acceptance gates.

## Decision

The recent Cedarbrook workflow defect/retest cycle is closed. **Broader beta release acceptance remains open; external invitations are not approved by this record.** The retained evidence spans several application versions and deliberate smoke scheduling. It is not a full release matrix or a fresh upload-to-export run on one final combined candidate.

This supersedes older pending summaries only for the verified rows below. It does not rewrite historical acceptance records or imply their tests ran again today.

## Release identity and CI

- PR #32 merged as `2783e36730ea4bb1cabc7e1be44020441e7be109`.
- [Post-merge CI](https://github.com/alinojoumi8/crowdlens/actions/runs/39164023823) passed backend, frontend and Docker. [PR CI](https://github.com/alinojoumi8/crowdlens/actions/runs/39163399651) passed 1,079 backend, 12 Node and 110 component tests, build, audits and Compose checks.
- Exact merged image smoke passed network-disabled non-root startup, healthy control storage, graceful shutdown and persistence after restart.
- Deployed revision remains `a517c68451af83a0e7d9b992d7f084bfd6f86682`; its tree equals merged main. Hosted and local source fingerprint: `9c199e0f1330ebf7cdd3663ae33d396a74809d378cb9ca5a0f39441fa5287337`.
- Prior CodeRabbit CLI review completed all four changed code/test files with zero findings. This closeout changes documentation only and received a focused consistency review; no new CodeRabbit run or application test rerun was needed. Lint/typecheck scripts are not configured.

## Consolidated operational matrix

| Criterion | Evidence and result | Boundary |
| --- | --- | --- |
| Fictional PDF upload and graph | Real provider/browser run; frozen input fingerprint `4c9cd90461c2216d2e2b39d6a4111eccb66d74550c0e0499efe9c81bfd1f0807` | Earlier build; not repeated on final candidate |
| Exact roster | Real preparation retained all four requested participants | One fictional fixture |
| Autonomous activity | Eight written model responses across two rounds, backed by transport receipts; initial/scheduled posts counted separately | Deliberate smoke scheduling; normal-mode participation not established |
| Root report and focused correction | Real three-section report; supported correction saved separately | Needs review; historical grammar and mixed scheduled/model citation findings remain |
| Safe refusal | Unsupported/unmapped summary stayed blocked; UI disabled save and API returned 409 | Expected refusal, not useful-completion quality |
| Timeout recovery | Saved draft audit retried once; repeated request key did not duplicate inference; adverse findings preserved | Earlier reviewed build, retained evidence |
| Full-section review | Explicit selected summary, complete source coverage, audited immutable revision | Selected scope only; inherited forecast/other sections not reverified |
| Summary save validation | Existing audited 293-character proposal saved without model calls | Current deployed code; source appendix did not bypass prose quotation checks |
| Enforced shortening | Real MiniMax drafting/audit shortened 1,478 to 394 characters; no blocking findings | Current source tree; one case, not a quality benchmark |
| Reopen/source links/export | Saved revision `report_21e5ec4ee41345a19a0465b04e4989a3`; browser/API/persisted Markdown identical; source link focused frozen excerpt | Current code, retained fictional input |
| Preservation/Stop | Parent, forecast, other sections and prior 43 receipts unchanged; only expected database changed among 5,813 preexisting files | Last live retest; no claim of universal deletion or power-loss durability |
| Layout | Desktop and 390px mobile inspected; no mobile overflow | Not complete keyboard, screen-reader, tablet or cross-browser acceptance |
| Request accounting | Same workflow stopped at 45/60 total, zero in flight, one historical unknown usage; two latest requests HTTP 200 with usage | No new inference or renewal in this closeout; billing total unknown |

Private source receipts remain under the local CrowdLens state directory: `live-acceptance-20261016-wde9pws8`, `minimax-section-recovery-20261018`, `summary-save-20261018`, `minimax-shortening-20261018`, and `beta-closeout-20261018`. Do not publish uploads, databases, credentials or private configuration with this record.

## Open release gates and disposition

| Gate | Status | Required closure |
| --- | --- | --- |
| T06 / B05 / B20 final-candidate matrix | Partial | Fresh single-candidate journey plus advertised file types, normal-mode activity if offered, ensemble/resume/rerun, required viewport/keyboard/error checks; any inference needs new explicit authorization |
| B01 scope/success contract | Open | Adopt target user/task, enabled features, limits, browsers, support, hosting region and budget; do not silently disable untested features |
| B02–B03 provider/privacy/distribution decisions | Open | Record owner decisions and required review for external use; successful inference is not proof of deployment suitability |
| B06 identity and invitations | Open, next implementation slice after prerequisites | Maintained authentication, API/session enforcement, invitation/recovery/revocation and admin/tester roles |
| B07–B08 ownership and administrator limits | Open | Two-user isolation across stores/jobs/downloads and server-owned quotas; local operator allowance is not identity or tenancy |
| B09–B19 external hardening and operations | Not closed by this evidence | Assess each enabled ingestion, network, job, monitoring, retention, deployment, accessibility and support requirement against its roadmap acceptance criteria |
| B21 capacity/failure envelope | Open | Measured supported load, overload/outage/write-failure behavior and admission limits |
| B22 output quality | Open | Representative current-model/build assessment with denominators and omissions; historical AI review remains AI evidence, not human or forecast validation |
| B23 security boundary | Open | Review and adversarial tests after authentication/isolation exist |
| B24 invited pilot / T12 external handoff | Open | Final release matrix, target-specific rehearsal, external-network tester journeys and adopted pilot criteria |

Previously completed local recovery/backup work is retained evidence; it does not close the external deployment gate. No new defect was reproduced in this documentation closeout. Known historical content-quality findings remain explicitly outside the selected-summary repair.

## Next sequence

1. Adopt the B01 beta scope and resolve B02–B03 owner decisions needed for the external target.
2. Implement B06 invitation/sign-in and session lifecycle, then B07 ownership and B08 administrator quotas.
3. Complete the combined-candidate B20–B23 acceptance, capacity, quality and security gates before B24 invitations.

Atlassian remains the current planning record. A fresh Jira search for unfinished CrowdLens/MiroFish issues returned no matches; this does not prove all Jira work is complete. T/B references are planning labels, not verified native Jira keys.
