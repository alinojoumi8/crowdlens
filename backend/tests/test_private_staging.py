"""Release admission must fail closed before touching existing deployment state."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('private_staging', ROOT / 'scripts/private_staging.py')
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)
IMAGE = 'sha256:' + 'a' * 64
REVISION = 'b' * 40


@pytest.fixture
def docker(monkeypatch):
    details = {'Id': IMAGE, 'Config': {'User': '1000:1000',
               'Labels': {'org.opencontainers.image.revision': REVISION}}}
    calls = []
    def fake(args, **kwargs):
        calls.append((args, kwargs))
        return json.dumps([details]) if args[:3] == ['docker', 'image', 'inspect'] else ''
    monkeypatch.setattr(staging, 'command', fake)
    monkeypatch.setattr(staging, 'build_proxy', lambda base: 'sha256:' + 'c' * 64)
    monkeypatch.setattr(staging, 'release_source', lambda revision: {
        'declared_revision': revision, 'source_sha256': 'd' * 64, 'scope': 'runtime-source-v2'})
    return details, calls


@pytest.mark.parametrize('image,revision,https,http', [
    ('crowdlens:latest', REVISION, 8443, 8080), (IMAGE, 'short', 8443, 8080),
    (IMAGE, REVISION, 443, 8080), (IMAGE, REVISION, 8443, 8443),
    (IMAGE, REVISION, 65536, 8080),
])
def test_invalid_release_never_creates_state_or_calls_docker(tmp_path, docker, image, revision, https, http):
    path = tmp_path / 'stage'
    with pytest.raises(ValueError):
        staging.initialize(path, image, revision, https, http)
    assert not path.exists() and not docker[1]


def test_existing_state_and_checkout_paths_are_not_overwritten(tmp_path, docker):
    existing = tmp_path / 'stage'
    existing.mkdir()
    (existing / 'sentinel').write_text('preserve')
    for path in (existing, ROOT / 'private-stage-state'):
        with pytest.raises(ValueError):
            staging.initialize(path, IMAGE, REVISION)
    assert (existing / 'sentinel').read_text() == 'preserve' and not docker[1]


@pytest.mark.parametrize('key,value', [('User', 'root'), ('Labels', {}), ('Labels', None)])
def test_wrong_image_identity_is_rejected(tmp_path, docker, key, value):
    docker[0]['Config'][key] = value
    with pytest.raises(ValueError, match='Image identity'):
        staging.initialize(tmp_path / 'stage', IMAGE, REVISION)
    assert not (tmp_path / 'stage').exists()


def test_fresh_releases_have_distinct_projects_and_private_credentials(tmp_path, docker):
    a, b = tmp_path / 'a', tmp_path / 'b'
    first = staging.initialize(a, IMAGE, REVISION)
    second = staging.initialize(b, IMAGE, REVISION, 9443, 9080)
    assert first['project'] != second['project']
    assert a.stat().st_mode & 0o777 == 0o700
    assert (a / 'release.env').stat().st_mode & 0o777 == 0o600
    assert (a / 'release.env').read_text() != (b / 'release.env').read_text()
    assert 'SECRET' not in json.dumps(first)
    assert staging.load_release(a) == first


@pytest.mark.parametrize('name', ['compose.yaml', 'Caddyfile', 'release.env'])
def test_configuration_drift_fails_before_compose(tmp_path, docker, name):
    path = tmp_path / 'stage'
    staging.initialize(path, IMAGE, REVISION)
    (path / name).write_text('changed')
    count = len(docker[1])
    with pytest.raises(ValueError, match='configuration changed'):
        staging.compose(path, 'up', '--detach')
    assert len(docker[1]) == count


def test_ambient_compose_and_staging_settings_cannot_override_release(tmp_path, docker, monkeypatch):
    path = tmp_path / 'stage'
    staging.initialize(path, IMAGE, REVISION)
    monkeypatch.setenv('COMPOSE_FILE', '/unrelated/private-stack.yaml')
    monkeypatch.setenv('CROWDLENS_STAGE_SECRET', 'unrelated-secret')
    staging.compose(path, 'config', '--quiet')
    args, kwargs = docker[1][-1]
    assert '--env-file' in args and str(path / 'release.env') in args
    assert 'COMPOSE_FILE' not in kwargs['env'] and 'CROWDLENS_STAGE_SECRET' not in kwargs['env']


def test_release_permissions_and_path_traversal_are_rejected(tmp_path, docker):
    path = tmp_path / 'stage'
    staging.initialize(path, IMAGE, REVISION)
    path.chmod(0o755)
    with pytest.raises(ValueError, match='0700'):
        staging.load_release(path)
    path.chmod(0o700)
    release = json.loads((path / 'release.json').read_text())
    release['files']['../unrelated.env'] = 'not-read'
    (path / 'release.json').write_text(json.dumps(release))
    with pytest.raises(ValueError, match='configuration changed'):
        staging.load_release(path)


@pytest.mark.parametrize('change', [None, 'dirty', 'untracked', 'index', 'missing'])
def test_release_source_matches_committed_runtime_not_only_a_label(tmp_path, monkeypatch, change):
    root = tmp_path / 'repo'
    helper = root / 'backend/app/utils/build_identity.py'
    helper.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / 'backend/app/utils/build_identity.py', helper)
    index = root / 'frontend/index.html'
    index.parent.mkdir()
    index.write_text('<title>Fictional</title>')
    subprocess.check_call(['git', 'init', '-q', str(root)])
    subprocess.check_call(['git', '-C', str(root), 'add', '.'])
    subprocess.check_call(['git', '-C', str(root), '-c', 'user.name=Fixture',
                           '-c', 'user.email=fixture@example.test', 'commit', '-qm', 'fictional fixture'])
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    monkeypatch.setattr(staging, 'ROOT', root)
    if change == 'dirty':
        helper.write_text(helper.read_text() + '\n# changed runtime\n')
    elif change == 'untracked':
        (helper.parent / 'extra.py').write_text('fictional = True\n')
    elif change == 'missing':
        revision = 'e' * 40
    elif change == 'index':
        index.write_text('<title>Uncommitted fixture</title>')
    if change:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            staging.release_source(revision)
    else:
        assert staging.release_source(revision)['declared_revision'] == revision
