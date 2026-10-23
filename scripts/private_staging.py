#!/usr/bin/env python3
"""Isolated, provider-disabled, loopback-only fictional-data staging.

Release state is private and outside the checkout. No command deletes data,
changes host trust, publishes images, or changes an existing deployment.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import secrets
import shutil
import subprocess
import tarfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'deploy/private-staging'
IMAGE_ID = re.compile(r'sha256:[0-9a-f]{64}')
REVISION = re.compile(r'[0-9a-f]{40}')
HOST = 'crowdlens-stage.localhost'


def command(args, **kwargs):
    return subprocess.check_output(args, text=True, timeout=kwargs.pop('timeout', 60), **kwargs).strip()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_proxy(base):
    image = command(['docker', 'build', '--quiet', '--pull=false', '--network', 'none',
                     '--build-arg', 'CADDY_BASE=' + base, '--file', str(TEMPLATES / 'Dockerfile'),
                     str(TEMPLATES)], timeout=120)
    if not IMAGE_ID.fullmatch(image):
        raise ValueError('Proxy build did not return an immutable image ID')
    return image


def release_source(revision):
    """Bind runtime-source-v2 to committed bytes, including dirty/untracked detection."""
    directories = ('backend/app', 'backend/scripts', 'frontend/src', 'frontend/public')
    fixed = ('package.json', 'package-lock.json', 'backend/pyproject.toml', 'backend/uv.lock',
             'backend/gunicorn.conf.py', 'backend/run.py', 'frontend/package.json',
             'frontend/package-lock.json', 'frontend/vite.config.js', 'Dockerfile')
    if command(['git', 'cat-file', '-t', revision], cwd=ROOT) != 'commit':
        raise ValueError('Select an available Git commit')
    changed = subprocess.run(['git', 'diff', '--quiet', revision, '--', *directories, *fixed,
                              'frontend', '.dockerignore'], cwd=ROOT)
    if changed.returncode:
        raise ValueError('Runtime build inputs differ from the chosen commit; use a clean runtime checkout')
    names = subprocess.check_output(['git', 'ls-tree', '-r', '-z', '--name-only', revision, '--',
                                     *directories, *fixed], cwd=ROOT).decode().split('\0')
    names = [n for n in names if n and (n in fixed or Path(n).suffix in {'.py', '.js', '.vue', '.svg'})]
    archive = subprocess.check_output(['git', 'archive', '--format=tar', revision, '--', *names], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        digest.update(name.encode() + b'\0')
        digest.update(hashlib.sha256(content).digest())
    identity = runpy.run_path(str(ROOT / 'backend/app/utils/build_identity.py'))['source_identity'](ROOT, revision)
    if identity['source_sha256'] != digest.hexdigest():
        raise ValueError('Runtime source differs from the chosen commit; use a clean runtime checkout')
    return identity


def compose(state, *args):
    release = load_release(state)
    # Shell/checkout .env and COMPOSE_* settings must not override this release.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('COMPOSE_', 'CROWDLENS_STAGE_'))}
    return command(['docker', 'compose', '--project-directory', str(state),
                    '--env-file', str(state / 'release.env'), '--file', str(state / 'compose.yaml'),
                    '--project-name', release['project'], *args], env=env, timeout=180)


def load_release(state):
    state = Path(state).resolve()
    if state.stat().st_mode & 0o077:
        raise ValueError('Release directory must have mode 0700')
    release = json.loads((state / 'release.json').read_text())
    if not re.fullmatch(r'crowdlens-stage-[a-z0-9-]+', release['project']):
        raise ValueError('Invalid staging project')
    for name, digest in release['files'].items():
        if name not in {'compose.yaml', 'Caddyfile', 'release.env'} or sha256(state / name) != digest:
            raise ValueError('Release configuration changed; initialize a separate release')
    if set(release['files']) != {'compose.yaml', 'Caddyfile', 'release.env'}:
        raise ValueError('Incomplete release configuration')
    return release


def initialize(state, image, revision, https_port=8443, http_port=8080, *, renewal_test=False):
    state = Path(state).absolute()
    if not IMAGE_ID.fullmatch(image) or not REVISION.fullmatch(revision):
        raise ValueError('Use an immutable sha256 image ID and a full Git revision')
    if (not all(isinstance(p, int) and 1024 <= p <= 65535 for p in (https_port, http_port))
            or https_port == http_port):
        raise ValueError('Use distinct unprivileged HTTP/HTTPS ports')
    if state.exists() or state.is_symlink():
        raise ValueError('Release state already exists; it will not be overwritten')
    if state.resolve().is_relative_to(ROOT):
        raise ValueError('Keep credentials, CA keys and release state outside the checkout')
    identity = release_source(revision)
    details = json.loads(command(['docker', 'image', 'inspect', image]))[0]
    if (details['Id'] != image or (details['Config'].get('Labels') or {}).get('org.opencontainers.image.revision') != revision
            or details['Config']['User'] != '1000:1000'):
        raise ValueError('Image identity, revision or non-root user does not match')
    proxy = json.loads((TEMPLATES / 'images.json').read_text())['proxy']
    if not re.fullmatch(r'caddy:[0-9.]+-alpine@sha256:[0-9a-f]{64}', proxy):
        raise ValueError('Proxy must use the pinned official image digest')
    command(['docker', 'image', 'inspect', proxy])
    proxy_base, proxy = proxy, build_proxy(proxy)
    project = 'crowdlens-stage-' + uuid.uuid4().hex[:16]
    state.mkdir(mode=0o700, parents=True)
    for name in ['compose.yaml', 'Caddyfile']:
        shutil.copyfile(TEMPLATES / name, state / name)
    if renewal_test:
        # Only the disposable integration rehearsal uses a short certificate.
        path = state / 'Caddyfile'
        path.write_text(path.read_text().replace('renew_interval 5m', 'renew_interval 5s')
                        .replace('lifetime 12h', 'lifetime 2m'))
    env = {'CROWDLENS_STAGE_APP_IMAGE': image, 'CROWDLENS_STAGE_PROXY_IMAGE': proxy,
           'CROWDLENS_STAGE_SECRET': secrets.token_urlsafe(48),
           'CROWDLENS_STAGE_HTTPS_PORT': str(https_port), 'CROWDLENS_STAGE_HTTP_PORT': str(http_port)}
    env_path = state / 'release.env'
    env_path.touch(mode=0o600)
    env_path.write_text(''.join(k + '=' + v + '\n' for k, v in env.items()))
    release = {'project': project, 'revision': revision, 'image': image, 'proxy_image': proxy,
               'proxy_base': proxy_base,
               'source': identity, 'https_port': https_port, 'http_port': http_port,
               'url': f'https://{HOST}:{https_port}', 'fictional_data_only': True,
               'auth_mode': 'local_loopback_only', 'provider_calls_enabled': False,
               'second_device': 'deferred_by_user',
               'files': {name: sha256(state / name) for name in ['compose.yaml', 'Caddyfile', 'release.env']}}
    (state / 'release.json').write_text(json.dumps(release, indent=2) + '\n')
    return release


def container(state, service):
    value = compose(state, 'ps', '--quiet', service)
    if not re.fullmatch(r'[a-f0-9]{12,64}', value):
        raise ValueError('Expected one running staging container for ' + service)
    return value


def export_ca(state):
    destination = state / 'root-ca.crt'
    deadline = time.monotonic() + 20
    while True:
        try:
            command(['docker', 'cp', container(state, 'proxy') + ':/data/caddy/pki/authorities/local/root.crt',
                     str(destination)], stderr=subprocess.DEVNULL)
            return destination
        except subprocess.CalledProcessError:
            if time.monotonic() >= deadline:
                raise ValueError('Proxy did not create its CA; inspect this release\'s proxy logs') from None
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'up', 'stop', 'ca'])
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--image')
    parser.add_argument('--revision')
    parser.add_argument('--https-port', type=int, default=8443)
    parser.add_argument('--http-port', type=int, default=8080)
    args = parser.parse_args()
    state = args.state.absolute()
    if args.action == 'init':
        if not args.image or not args.revision:
            parser.error('init requires --image and --revision')
        release = initialize(state, args.image, args.revision, args.https_port, args.http_port)
        print(json.dumps({'state': str(state), 'url': release['url'], 'project': release['project']}))
    elif args.action == 'up':
        print(compose(state, 'up', '--detach', '--wait', '--wait-timeout', '120'))
        print(export_ca(state))
    elif args.action == 'stop':
        print(compose(state, 'stop'))
    else:
        print(export_ca(state))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc)) from None
