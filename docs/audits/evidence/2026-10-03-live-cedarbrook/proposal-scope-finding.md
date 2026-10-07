# Real general-report proposal scope failure

At 05:16:48 America/Toronto on 2026-10-03, visible Draft with sources for section 1 of report_38eb8454832e returned HTTP 409 and displayed "missing or inconsistent scope". The real provider ledger remained at 39 admissions, none in flight or unknown. Stopped via the visible workflow control before repair.

The completed general-prediction report has source_grounding={}; both actual simulation configurations lack case_id/case_version_id. The upload project persists case_a1b28cf9ada0/casever_88fa1e1ffa14 and that exact immutable case version matches project proj_83707effff70 and graph 88956ccc-ea07-47a7-807d-4fc391ce2489. The existing strict source_scope correctly rejected the absent IDs. This was an application workflow coverage gap, not a provider failure.

The original failed proposal record proposal_7b76f48edeb74d95a3bc6034f99f3d05 is retained with state=failed,error_code=admission_failed; its record/hash is in receipts/proposal-scope-failed-artifacts.json. Screenshot 10-proposal-scope-failure.jpg retains the user-visible error. No parent report or original config was edited to supply IDs.

Minimal repair: proposal admission first retains existing strict scope validation. For incomplete legacy general-report scope, consult persisted project/case metadata, require exactly one version matching the saved simulation project ID and graph ID, reject all conflicting supplied scope, and re-run strict validation. Never choose the latest version implicitly or modify the root report. A fully valid existing scope is unchanged.

Fail-first API regression reproduced 409 instead of 202; six wrong/missing/ambiguous scope cases still reject without a model factory call. Positive coverage includes a newer unrelated case version, actual proposal drafting against controlled sources, and byte-identical parent artifacts. Original and final logs retained.
