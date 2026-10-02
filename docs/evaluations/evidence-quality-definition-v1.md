# Evidence-quality v1: frozen pre-baseline definition

Date: 2026-10-02. Application baseline: `fbedf59752fbc3387e4aa164c2f6f5869d4744de`
(H1 code at `33d87c82c5f3ecb3435ba86a5160a44f79635443`, plus preserved M1 docs).

The [manifest](../../backend/tests/fixtures/evidence_quality/v1/manifest.json)
freezes synthetic sources, hashes, expected structural outcomes and hard invariants
before any evaluation run. Its expected assertions are authored test contracts,
not independently assessed factual labels. The development case and fourteen
holdout cases have disjoint case, graph, version, document and episode identities.
The fixture author knows the synthetic holdout. No prompts are tuned here.

Use the existing pytest runner for deterministic checks and repeat it three times.
The denominator is every selected test, including failed, skipped or blocked tests.
First-attempt success is passed tests / collected tests on run one. Repeat stability
is test identities passing all three runs / union of collected identities. Failures,
errors, skips, blocked workflow outputs and ready outputs are recorded separately.
A correctly blocked invalid proposal passes its safety assertion but contributes
no successful draft and no quality accuracy. Never report blocked model work as
zero errors or a successful generation. Model-output quality, attribution accuracy,
unsupported-claim rate, omissions, human time and cost remain null without actual
outputs and independent labels. Structural source-ID validity is a distinct metric.

The corpus covers direct support, invalid source references, conflicts, absence,
foreign case/graph, wrong version, simulation/report/memory origins, missing
attribution and malformed ledger schema. A deliberately unsupported claim with a
valid source reference documents the semantic gap: a permissive deterministic
audit can leave the proposal ready. Ready therefore cannot be a factual label.

Fault tests in `test_evidence_quality_faults.py` freeze two root-admission safety
assertions: a lost response followed by a same-key retry, and simultaneous requests,
must dispatch and persist at most one task. Flask routing, SQLite and task admission
are real; generation dispatch is captured. This can reproduce duplicate work
admission, not expensive inference or duplicate completed report artifacts.
An injected transport timeout characterizes aggregate retry amplification using
simulated elapsed time. No actual provider request or long sleep is performed.
Its observation is not an invented root deadline or a model latency measurement.

Human packets will omit fixture category, expected findings and provider identity;
their administrative mapping stays separate. Reviewers supply their own identity,
source, timestamps and measured duration. Disagreements remain separate rows.
Blank forms do not count as review. No performance or model-quality thresholds
are selected after observing results; all structural hard invariants must pass.

ECC 2.2.3 `eval-harness` and `ai-regression-testing` inform this protocol. No ECC
candidate gate, alternative executor, receipt-based containment claim, external
evaluation platform, hosted inference, generation-model download or policy
activation is used. Existing repository-native tests are explicitly authorized.
