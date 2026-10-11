# CI and production releases

The canonical repository is **alinojoumi8/crowdlens** (local remote `crowdlens`).
The legacy public `origin` is not the destination for current private changes.
Develop on `codex/*`, run `UV_PYTHON=3.11 npm run check`, and require successful
backend, frontend and Docker checks on the exact candidate before integration.
GitHub plan/ruleset enforcement is separate from workflow dependencies; do not
infer branch protection from a green check.

## Production image

Docker builds the Vue frontend with pinned Node 22 and installs the frozen
Python lockfile. The final image runs Gunicorn as UID/GID 1000; Node, Vite and
Flask's development server are not runtime processes. One threaded worker owns
background tasks and simulation subprocesses. Preloading, extra workers and
request-count recycling are rejected at startup. Horizontal scaling requires
externalizing task ownership first.

The same server serves the SPA and API on ports 3000 and 5001. Missing API and
asset paths return 404, SPA history routes return an uncached index, and hashed
assets receive immutable caching. Compose binds both ports to loopback and
allows 60 seconds for shutdown (Gunicorn's worker grace is 45 seconds).

```sh
CROWDLENS_BUILD_REVISION="$(git rev-parse HEAD)" docker compose build mirofish
python3 scripts/smoke_container.py --image mirofish-local-mirofish \
  --revision "$(git rev-parse HEAD)" --output /tmp/crowdlens-smoke.json
docker compose up -d --no-deps mirofish
```

Use a clean checkout for a declared Git revision. `/health` and `/api/status`
include that revision and an independent source fingerprint. For older installs,
stop the app and back up uploads before changing ownership: the app UID/GID
must own its upload database and artifacts. `CROWDLENS_UID`/`CROWDLENS_GID` can
match another host owner. Never recursively change shared Neo4j/Ollama volumes.
Only the app is recreated by the last command; dependencies must already run.

## Image smoke and release gate

Normal Actions CI tests Python and Vue, builds the frontend, audits JavaScript
packages, validates Compose, and builds/smokes the production image. The smoke
runs with `--network none`, a disposable Docker volume and dummy credentials.
It verifies the actual image's revision, non-root execution, API/static routing,
graceful stop, restart, and persisted database/artifact data. It cannot make
provider calls and does not establish generation or graph quality.

The release workflow accepts only existing stable `vX.Y.Z` tags whose commits
belong to canonical main. It reuses CI to validate that exact SHA, then builds
one image, smoke-tests it, and pushes that same image under its version tag.
An existing version or an ambiguous registry lookup fails closed. Download the
`release-receipt` Actions artifact for the image ID, source identity, smoke result
and registry digest. Consume `ghcr.io/alinojoumi8/crowdlens@sha256:...` for an
immutable deployment reference; a tag alone is not an immutable registry policy.

Tag pushes do **not** update `latest`. For an explicit promotion, manually run
`Publish validated release image` with a new stable tag and `promote_latest=true`.
Its candidate must still be main HEAD immediately before publishing. Releases
are serialized. The workflow does not publish multi-architecture images, SBOMs
or attestations; those are separate additions, not implied by smoke success.

## Rollback and retained state

Before replacement, record the previous image ID/digest and privately retain the
runtime environment plus a cold backup of uploads and graph state as applicable.
Stop the app, restore a state-compatible backup when a migration requires it,
then start the previous image against that restored state. Never test a rollback
by mounting live data into two app containers. Verify report/source hashes,
control-database health and runtime identity after replacement. A failed or
interrupted generation requires explicit operator recovery; a restart is not
permission to spend again.

## Optional CircleCI fallback

`.circleci/config.yml` is opt-in (`run_validation=false` by default), preserving
the earlier local draft's intent. It validates the same backend/frontend and
builds/smokes the image after those tests pass. It never publishes. Validate its
schema with `circleci config validate .circleci/config.yml` before enabling a
canonical project trigger. No successful cloud CircleCI execution is claimed.
Record an exact revision and workflow URL before using it as fallback evidence.

## Evidence

The baseline `3e9ab7235140de248e433338b401274b29218cc1` passed
[Actions CI](https://github.com/alinojoumi8/crowdlens/actions/runs/38051735064).
New implementation validation and runtime deployment receipts are recorded in
[the delivery sequence](tasks/2026-10-10-delivery-sequence.md), then in the PR.
A workflow definition is not evidence of an actual registry publication.

Production serving follows [Flask's Gunicorn deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/).
