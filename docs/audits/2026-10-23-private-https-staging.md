# B10 private HTTPS staging: local verification

Verified October 23, 2026, on `codex/private-https-staging`. The target is a new, isolated Docker Compose project on the existing local host, with fictional fixtures and provider access disabled. This is the local B10 implementation slice. The real second-device check was deferred by the user; a separate-host rebuild and broader beta-hosting acceptance remain unverified.

Runbook: [private staging](../private-staging.md).

## Release identity

| Boundary | Verified value |
| --- | --- |
| Application commit | `f4f2c3b7c6ace08a318e0ccdf174edc0174c1479` (merged B09) |
| Build context | Committed Git archive, excluding local ignored/untracked state |
| Running application image ID | `sha256:99fa2129592050c1354720cce3b3c78fa9989807c05d554d10c02122f49d69c6` |
| Running proxy image ID | `sha256:a579c9614310460964e571a622dfbc103f3b9e61e30f293a32a55dd7f4dd4b67` |
| Proxy base | Official Caddy 2.11.7 Alpine, pinned in `deploy/private-staging/images.json` |
| Runtime source fingerprint, before and after restart | `a9a21276ac64f2f503e3e32e6e329aca42ae7e6f7f6c4f020b58212576b4e4f7` |
| Built JavaScript asset | `/assets/index-DyaewMix.js` |
| Local URL | `https://crowdlens-stage.localhost:8443` |

The release bundle records immutable image IDs, revision, source identity, random project, ports and configuration hashes. Initialization rejects a mutable app tag, mismatched image revision/user, dirty or untracked runtime source, changed tracked build inputs, existing state, checkout-local state, invalid ports and drifted configuration. A regression first reproduced an uncommitted HTML entry point escaping the narrower runtime fingerprint; the release guard now rejects that change too.

## Observed runtime checks

- TLS validates with the exported private CA and expected hostname. System-default trust, a peer's CA and an unrelated hostname are rejected. No host trust store was modified.
- HTTP redirects to the fixed HTTPS origin. Foreign Origin/Host requests and private paths are refused; invalid API/asset paths return 404, and the intended SPA fallback works.
- Actual Docker mappings expose only the proxy's two IPv4 loopback ports. The app publishes no backend/management port and has only its internal application network. Serving processes are UID 1000, with read-only roots, all capabilities dropped and bounded CPU/memory/PIDs/logging.
- Application/log/CA volumes belong only to the new random project. A second fresh configuration has distinct volumes, credentials and CA; the first release's fictional SQL row/file are absent there. Existing app/Neo4j/Ollama services and historical data are not mounted into staging.
- A clean stop exits without OOM or forced termination. Fictional SQL/file fixtures, the private CA and exact runtime identity survive startup again.
- A separate two-minute-certificate rehearsal observed automatic renewal with a different serial and later expiry, validated by the unchanged CA. Normal staging uses twelve-hour leaf certificates. Companion rehearsals are stopped; their data/receipts are retained.
- Chromium inspected the built homepage at desktop and 375 px: expected provider-disabled status, empty history, no failed/off-origin requests or JavaScript errors, and no horizontal overflow. The rendering-only browser context ignored certificate warnings; TLS trust/hostname checks above used actual certificate verification separately.

Private receipts, logs, release bundles and screenshots are retained at `/home/ali/.local/state/crowdlens/b10-20261023-pv2lqigg/`. The live release is its `stage/` directory. Environment files and CA private keys are not part of this source change.

## Checks and review

`UV_PYTHON=3.11 pnpm check` passed 1,240 backend tests, 12 frontend unit tests, 128 component tests and production build on Node 22.23.2 / Python 3.11. The 20 staging tests cover release admission, configuration isolation/drift and committed-source identity. Root/frontend audits report zero vulnerabilities. Existing Compose configuration, actual staging startup/configuration, whitespace and scoped secret checks passed. Lint/typecheck scripts are unconfigured.

CodeRabbit CLI 0.9.1 completed a review of all eight implementation/test/runbook files in an isolated clone with canonical `alinojoumi8/crowdlens` origin and raised 0 issues. Those files byte-match the reviewed snapshot. This audit is a documentation-only addition reviewed against the retained receipts. No paid credits or review-trigger comments were used.

## Remaining acceptance and next delivery

Local mode is not authentication; this release must stay loopback-only with fictional data. Model, embedding and graph dependencies are intentionally unavailable, and the UI reports that state. This is not complete workflow, factual-quality, capacity or external-beta acceptance. The resource limits are not physical disk quotas or a complete parser/filesystem sandbox.

The real second-device HTTPS check is deferred. A separate clean-host rebuild, real OIDC/MFA/recovery, hosted beta data isolation and combined acceptance remain open. The next delivery step is the B10 PR and hosted CI, followed by authorized merge/post-merge verification. Complete the deferred host/device gate when available; B11 is the next implementation area for coordinated networking, secrets and dependency-version verification on shared services.
