# Comparable evaluation after root-admission repair

Date: 2026-10-02. Executed by the coordinating agent on its integration worktree;
the evaluation specialist inspected and preserved the resulting artifacts.

**The same 164 deterministic checks pass on all three runs: 492/492.** This
establishes the local structural after result for the identified candidate.
Real-model quality remains **BLOCKED** and all four human packets **PENDING**.

| Identity | Value |
| --- | --- |
| Exact tested commit | `e5108ca62c63e91980183d658fd706fb48f1f21d` |
| Dirty/untracked inputs | Empty; before/after input identities match |
| Runtime-source-v1 SHA-256 | `2e7ba27c42b2518e37b682a3c7acd5e60e50f3747dbb259d536834727d94c2fe` |
| Full allowlisted input manifest SHA-256 | `4bd3b8328648eeb4b08044f6df819afd62de44b6c89910038ffae59727ae0f20` |
| Fixture manifest SHA-256 | `78dc98ecd30ac22f14aa40c4ae8635145b43801f257af623f7d00abe89a5b12f` |
| First-attempt / any-of-three / all-three | Each 164 / 164 = 100% |
| Errors, skips, missing observations | Zero |
| Run wall times | 6.209, 5.951, 5.851 seconds |
| Corpus workflow per run | 5 ready (including one development), 10 blocked |
| Corpus substitute calls | 18 per run; 54 total; zero real model calls |

Command from integration root, **exit 0**:

```bash
backend/.venv/bin/python backend/scripts/evaluate_evidence_quality.py \
  --output-dir /tmp/crowdlens-ecc-eval-after-root-20261002 --repeats 3
```

The [complete result](results/2026-10-02-after-root/results.json),
[run 1](results/2026-10-02-after-root/run-1.xml),
[run 2](results/2026-10-02-after-root/run-2.xml),
[run 3](results/2026-10-02-after-root/run-3.xml), companion text logs,
identity manifest and human packets are preserved byte-for-byte.
[Receipt hashes](results/2026-10-02-after-root/receipt-sha256.json) verify the copies.
The earlier [before baseline](2026-10-02-evidence-quality-baseline.md) remains red
at its exact source identity.

Source comparison confirms matching frozen corpus and drafting prompt hashes.
The selected test definitions were unchanged between the comparable runs. The
allowlisted input manifest differs in `backend/app/api/report.py`, the new
`backend/tests/test_report_admission.py`, and the release owner's newly added
`check_ecc_backup.py`/`check_ecc_services.py` scripts. Only the root API repair
changes the exercised application behavior in this comparison. The additional
admission tests are part of the coordinator's broader suite, not the frozen
164-test selection.

Both fail-first root faults now persist and dispatch one task: identical-key
response-loss replay and concurrent identical requests. The transport probe still
records 1530 simulated seconds at its default per-attempt retry settings. Its
passing assertion is characterization, not acceptance of a whole-report budget.
No quality threshold was added or prompt tuned against the holdout.

After this comparable run, the human-importer review added three explicit schema
and partial-review regression cases, bringing the evaluator selection to 167
tests. Their focused suite passed eleven tests, but that does not relabel this
164-test receipt as a later candidate run. The release owner must verify the
frozen final candidate with all integrated changes. No remote CI, deployment,
real-provider workflow or independent human adjudication is claimed here.
