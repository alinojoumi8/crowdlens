"""Non-secret identity of runtime source, independent of operator data/configuration."""
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import re


def source_identity(root, revision=None):
    root = Path(root)
    paths = set()
    for directory in ('backend/app', 'backend/scripts', 'frontend/src', 'frontend/public'):
        paths.update(p for p in (root/directory).rglob('*')
                     if p.is_file() and p.suffix in {'.py', '.js', '.vue', '.svg'} and not p.is_symlink())
    for name in ('package.json', 'package-lock.json', 'backend/pyproject.toml', 'backend/uv.lock',
                 'frontend/package.json', 'frontend/package-lock.json', 'frontend/vite.config.js', 'Dockerfile'):
        if (root/name).is_file(): paths.add(root/name)
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {'declared_revision': revision if isinstance(revision, str) and re.fullmatch(r'[0-9a-f]{40}', revision) else None,
            'source_sha256': digest.hexdigest(), 'scope': 'runtime-source-v1'}


@lru_cache(maxsize=1)
def runtime_identity():
    return source_identity(Path(__file__).resolve().parents[3], os.environ.get('CROWDLENS_BUILD_REVISION'))
