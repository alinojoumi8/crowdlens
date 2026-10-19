# Private pilot scope and provider/privacy decisions

Adopted for implementation on 2026-10-18 from the user's explicit selections: **local/private, fictional data only, no new paid services; standards-based OIDC with a disposable local test provider.** This is the current pilot contract, not approval for an externally hosted beta.

## Scope and success

- Target: the operator explores fictional scenarios and reviews evidence; up to two synthetic tester identities exercise invitations and sign-in locally. No invitation messages are sent automatically.
- Host: existing local machine, loopback only. No hosting region is selected because no external host is authorized. Incremental infrastructure, authentication and provider purchasing budget: $0.
- Operator scenario workflow: the retained fictional Cedarbrook PDF, four participants and two deliberately scheduled smoke rounds. No prediction-accuracy claims. Other file types, URL ingestion, ensemble flows and normal-mode participation are outside this pilot's acceptance promise, not silently removed from the existing local application.
- Authentication stage: administrator plus tester roles; 24-hour single-use email-bound invitations, eight-hour session maximum and 30-minute idle expiry. Administrative suspension and sign-out-all revoke sessions immediately. OIDC accounts require verified email; admin sign-in requires a validated `amr` containing `mfa`.
- Tester project access: denied until workspace isolation and administrator-owned quotas are implemented and tested. Existing private local data is not migrated into a shared tester environment.
- Supported acceptance browser: Chromium desktop and narrow mobile viewport, keyboard navigation on account screens. Other browsers and assistive technologies remain release checks, not certified support.
- Operator support: the person who invited the tester, through the existing agreed private channel, best effort with no SLA. Never invent an email address or promise support hours.
- Success: invited synthetic identities can sign in, wrong/unverified/expired identities fail, replay fails, session expiry/revocation/suspension works, anonymous downloads fail, testers cannot administer or access shared resources, and the local operator's existing data and closed allowance remain intact.
- Stop/rollback: suspend test access and stop the isolated verification app on failed auth/privacy checks. Do not expose the current local-mode service or replace its runtime until real provider configuration and a preserved-data rollout are verified.

## Provider decision

Retain MiniMax-M3.1-Flash-Preview for explicitly authorized operator experiments only; do not switch models, purchase services or renew inference implicitly. Existing workflow remains stopped at 45/60. Each future experiment needs its own explicit time allowance under that retained total ceiling, or a separately agreed new workflow budget. This document grants none.

The [official model guide](https://platform.minimax.io/docs/guides/text-generation), checked 2026-10-18, lists this preview through M Plan and MiniMax Code. Successful requests establish account access for the recorded test, not permission, pricing or capacity for a hosted multi-user service. We do not assert provider data residency, no training, zero retention, SLA or permitted resale. Those external-service decisions remain gated pending account-specific terms and operator review. No customer or legal-case material is authorized for this pilot. Ollama embeddings remain local; there is no remote embedding fallback.

Identity: use Authlib's maintained [Flask OIDC client](https://docs.authlib.org/en/latest/oauth2/client/web/flask.html), authorization code flow with PKCE, state, nonce and signed ID-token validation. Production identity provider credentials are not available; an actual provider must be configured and its MFA/recovery behavior verified before non-synthetic identities are admitted. The loopback fixture is deliberately not an identity service and must never be deployed as one.

## Privacy and acceptable use

- Only invented test data is permitted. Exclude real legal filings, personal information, secrets and confidential business material.
- Files, extracted text, graph records, simulations, reports, revisions and reviews live on the local host and can be read by its operator. Authorized model calls transmit selected sources/prompts to MiniMax; that is not local-only processing.
- Identity provider handles passwords, MFA and recovery. CrowdLens stores issuer/subject, verified email, role, suspension state, hashed invitation/session tokens and session timestamps in a separate local SQLite database. OAuth access/refresh tokens are not persisted.
- Cookies support OIDC state, an HttpOnly opaque session and a readable CSRF token. No analytics service is added. Existing local operational logging remains. The authentication module does not deliberately log credentials, invitation codes or tokens; configure server/proxy access logs to omit callback query strings, and protect operational logs. The disposable fixture logs stay in private local verification storage.
- There is no automatic complete erasure or retention guarantee. Existing project deletion does not purge all related case/report/history/backup stores. Contact the operator for coordinated access/deletion; backups need separate treatment. This pilot does not promise a deletion deadline that the software cannot meet.
- Do not attempt unauthorized access, impersonation or quota bypass. Generated output remains exploratory and needs review; do not represent it as factual certification or professional advice.
- The sign-in screen links the same notice before any account access. Notices are limited to this private pilot. External privacy terms, data processing agreements and distribution decisions remain separate adoption/review gates.

## Source and license disposition

The project declares AGPL-3.0; retain its LICENSE and existing third-party notices. Authlib is added through the existing Python dependency/lock workflow; do not change package managers or remove notices. The local fixture and changed source remain available in this checkout to its operator. No external distribution or source-access compliance claim is made. Before network users receive the service, provide accessible corresponding source/notices and review the applicable application/PDF/dependency obligations. A private repository link alone is not an adopted external distribution plan.

## B01–B03 status

The local fictional-only scope and $0 incremental-services decision are adopted. Provider use and privacy handling are bounded as above. The broader hosted versions of B01–B03 are **not closed**: external hosting/budget, actual identity provider, account-specific model terms, privacy/distribution adoption and real-user data handling are deliberately excluded. B06 integration can be tested locally; B07 isolation and B08 admin quotas remain prerequisites for tester project access.
