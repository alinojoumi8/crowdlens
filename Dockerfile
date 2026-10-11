# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-bookworm@sha256:3fd8382c50bae84184460a6e1a8ff4eeac0e3ca6a560691cb56bd84d2b6ec9ca
COPY --from=ghcr.io/astral-sh/uv:0.9.26@sha256:9a23023be68b2ed09750ae636228e903a54a05ea56ed03a934d00fe9fbeded4b /uv /uvx /bin/
ENV UV_FROZEN=true UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/run.py backend/gunicorn.conf.py ./
# Retain the non-secret source inputs used by the runtime fingerprint.
COPY package.json package-lock.json Dockerfile /app/
COPY frontend/package.json frontend/package-lock.json frontend/vite.config.js /app/frontend/
COPY frontend/src /app/frontend/src
COPY frontend/public /app/frontend/public
COPY --from=frontend /build/dist /app/frontend/dist
RUN groupadd --gid 1000 crowdlens && useradd --uid 1000 --gid 1000 --no-create-home crowdlens \
    && mkdir -p /app/backend/uploads /app/backend/logs \
    && chown -R 1000:1000 /app/backend/uploads /app/backend/logs
ENV FRONTEND_DIST_DIR=/app/frontend/dist CROWDLENS_BIND=0.0.0.0:3000,0.0.0.0:5001
USER 1000:1000
ARG CROWDLENS_BUILD_REVISION
LABEL org.opencontainers.image.revision=$CROWDLENS_BUILD_REVISION
ENV CROWDLENS_BUILD_REVISION=$CROWDLENS_BUILD_REVISION
EXPOSE 3000 5001
STOPSIGNAL SIGTERM
CMD ["/app/backend/.venv/bin/gunicorn", "--config", "gunicorn.conf.py", "app:create_app()"]
