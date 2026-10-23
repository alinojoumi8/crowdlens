# Private HTTPS staging

B10's first target is a separate Docker Compose project on the existing local host. It is a fictional-data, provider-disabled rehearsal, not an external beta deployment. No paid host, domain, public CA or model service is needed. The second-device check was explicitly deferred by the user. Do not mark the broader B10 hosting acceptance complete until that check and the intended host have been verified.

The default URL is `https://crowdlens-stage.localhost:8443`, with HTTP on port 8080 redirecting to it. Both ports bind only to IPv4 loopback; there is no LAN/public listener. The dedicated `.localhost` hostname avoids setting browser HTTPS policy for other local applications. Caddy uses its own persistent private CA with automatic leaf renewal. Its root is exported for explicit client trust; the scripts never install trust globally. A browser without this CA will show a certificate error. Do not use `curl -k` as verification.

This local-only configuration deliberately retains `AUTH_MODE=local`. Local mode is not authentication. Do not forward these ports, change their bind address, or expose this stack to testers. Real OIDC configuration, MFA/recovery and tester admission remain separate gates described in [authentication](authentication.md). All provider/database endpoints point to a closed local port, model auto-pull is off, and the app has only an internal Docker network. The status API must report unavailable external dependencies rather than pretend the complete workflow is healthy. There are no model calls in this rehearsal.

Each release has a random Compose project, new application/log/CA volumes and random private SECRET_KEY. No root `.env`, existing data volumes, existing Neo4j/Ollama or historical uploads are used. App serving and proxy processes run as UID 1000 with read-only roots, all capabilities dropped, CPU/memory/PID limits and bounded logs. Initialization builds a small derivative of the pinned official proxy image, removing its privileged-port file capability and setting ownership of its new volume directories. Both running images are pinned by immutable local ID. One app worker remains mandatory. These are resource limits, not physical disk quotas or a complete native-parser sandbox.

## Build and initialize

Prerequisites: Linux Docker Engine with Compose, Python 3.11, Git, and sufficient free space for the app image (about 14 GB before shared layers). Use the dedicated B10 deployment checkout; keep state outside every Git checkout. The app image is selected by immutable local image ID, and the official Caddy image is pinned by registry digest in `deploy/private-staging/images.json`. No image is pushed by this workflow.

```bash
git rev-parse HEAD
# Set the verified full application revision from this checkout.
CROWDLENS_STAGE_REVISION=$(git rev-parse HEAD)
git archive --format=tar "$CROWDLENS_STAGE_REVISION" | docker build --build-arg CROWDLENS_BUILD_REVISION="$CROWDLENS_STAGE_REVISION" --tag crowdlens:private-stage -
docker image inspect crowdlens:private-stage --format '{{.Id}}'
docker pull caddy:2.11.7-alpine@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f
```

The archive build sends committed files only, excluding local environment files, uploads and other untracked/ignored state. Choose a new absolute private state path and pass the full image ID printed above. Initialization compares committed runtime bytes with the checkout, rejecting dirty/untracked runtime source (and tracked build-input changes such as the HTML entry point), then refuses existing state, mutable app tags, root images, mismatched revisions, checkout-local state and privileged/colliding ports. It creates a portable configuration bundle and non-secret release record, with the environment file protected as mode 0600. `up` verifies the bundle hashes and prevents ambient Compose/staging environment settings from overriding it.

```bash
python scripts/private_staging.py init --state /absolute/private/stage --image sha256:FULL_IMAGE_ID --revision FULL_REVISION
python scripts/private_staging.py up --state /absolute/private/stage
curl --resolve crowdlens-stage.localhost:8443:127.0.0.1 --cacert /absolute/private/stage/root-ca.crt https://crowdlens-stage.localhost:8443/
python scripts/verify_private_staging.py --state /absolute/private/stage
python scripts/private_staging.py stop --state /absolute/private/stage
```

`up` restarts an existing release without replacing its key or data. `stop` retains all volumes and release files. There is deliberately no delete/reset action. Keep CA private keys and environment files private; only distribute the public `root-ca.crt` to an explicitly authorized client. To transfer the exact image to another private host without a registry, use `docker image save`/`docker image load`, verify the archive's SHA-256 before loading, and compare the loaded image ID with `release.json`. Build a **new** release on that host; do not copy the staging environment or CA into another environment. Do not share beta credentials or volumes.

## Verification and renewal rehearsal

The verifier checks actual image/revision/source identity, trusted TLS and hostname rejection, HTTP redirects, blocked private routes, SPA/API/asset fallbacks, foreign Origin/Host rejection, loopback port mappings, internal application networking, volume mounts, process limits, graceful stop and SQL/file persistence after restart. It creates only a new fictional fixture row and file per run; it does not delete or alter existing application records. The resulting `verification.json` is a private delivery receipt.

Initialize and start a second fresh release on ports 9443/9080, then pass `--peer-state /absolute/private/peer` to verify distinct storage, secrets and CAs and the absence of the first release's fixture in its peer. This is an isolation rehearsal on one host; it is not the deferred second-machine acceptance check.

For a disposable renewal rehearsal, the Python initializer's `renewal_test=True` option creates a separate release with two-minute certificates and five-second renewal checks. Start it on unused ports and run the verifier with `--wait-renewal 180`. It must observe a new leaf serial with a later expiry while the original CA still validates the connection. Normal staging uses twelve-hour leaves and five-minute renewal checks. Preserve the receipt; stop the rehearsal afterwards. Do not shorten certificates on an active pilot or edit a bundle in place.

The [Caddy internal issuer](https://caddyserver.com/docs/caddyfile/directives/tls) manages local certificates without public ACME/DNS, and [automatic HTTPS](https://caddyserver.com/docs/automatic-https) requires clients to trust that CA explicitly. [Docker internal networking](https://docs.docker.com/compose/how-tos/networking/) limits external routing; it does not replace host firewall verification or protect unrelated services already exposed by the host. Coordinating those shared services remains B11.

Before moving beyond this host, verify the intended HTTPS URL from the real second device, its trusted CA and invalid-host behavior, the fresh-host runbook, and the recorded deployed image/revision/fingerprint. Keep actual IdP and combined workflow/load/recovery acceptance open until observed at that boundary.
