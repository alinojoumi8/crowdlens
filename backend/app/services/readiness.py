"""Cached, bounded metadata and storage probes. Never submit model inputs."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from urllib.parse import urlsplit

import requests


class ProbeCache:
    """Single flight per process; concurrent readers never queue behind a probe."""
    def __init__(self, ttl=60):
        self.ttl = ttl
        self.lock = threading.Lock()
        self.values = {}
        self.running = set()

    def get(self, key, probe):
        with self.lock:
            cached = self.values.get(key)
            if cached and time.monotonic() - cached[0] < self.ttl:
                return {**copy.deepcopy(cached[1]), 'cached': True}
            if key in self.running:
                return dict(state='checking', healthy=False, message='A metadata check is in progress.',
                            checked_at=None, cached=False, inference_verified=False)
            self.running.add(key)
        try:
            result = {**probe(), 'checked_at': datetime.now(timezone.utc).isoformat(),
                      'cache_seconds': self.ttl, 'cached': False}
            with self.lock:
                if len(self.values) >= 32:
                    self.values.pop(next(iter(self.values)))
                self.values[key] = (time.monotonic(), copy.deepcopy(result))
            return result
        finally:
            with self.lock:
                self.running.discard(key)


MODEL_CACHE = ProbeCache()
DISK_CACHE = ProbeCache()


def model_metadata(provider, base_url, model, api_key=None):
    provider = (provider or '').strip().lower()
    key = (provider, base_url, model, hashlib.sha256((api_key or '').encode()).hexdigest())
    result = MODEL_CACHE.get(key, lambda: _model_metadata(provider, base_url, model, api_key))
    return {'provider': provider, 'model': model, **result}


def _model_metadata(provider, base_url, model, api_key):
    result = dict(provider=provider, model=model, configured=False, reachable=None,
                  model_available=None, healthy=False, inference_verified=False, probe='model_metadata_get')
    def outcome(state, message, **extra):
        return {**result, 'state': state, 'message': message, **extra}
    if not base_url or not model or (provider != 'ollama' and not api_key):
        return outcome('unconfigured', 'Set the generation endpoint, model and required credentials.')
    result['configured'] = True
    try:
        parsed = urlsplit(base_url)
    except ValueError:
        return outcome('unconfigured', 'The configured endpoint URL is invalid.')
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return outcome('unconfigured', 'Use an HTTP(S) endpoint without embedded credentials, query or fragment.')
    if provider not in {'ollama', 'openai', 'minimax', 'gemini'}:
        return outcome('unverified', 'This provider has no supported non-generation metadata check.')
    base_url = base_url.rstrip('/')
    url = (base_url.removesuffix('/v1') + '/api/tags') if provider == 'ollama' else base_url + '/models'
    headers = ({'x-goog-api-key': api_key} if provider == 'gemini' else {'Authorization': 'Bearer ' + api_key}) if api_key else {}
    try:
        started = time.monotonic()
        # No redirects, retries, generation, embeddings, model pulls or source text.
        with requests.get(url, headers=headers, timeout=(1, 2), allow_redirects=False, stream=True) as response:
            result['reachable'] = True
            if response.status_code in {404, 405}:
                return outcome('unverified', 'Endpoint reachable; model metadata is unsupported. Inference is untested.')
            if response.status_code in {401, 403}:
                return outcome('unavailable', 'Metadata access was denied. Check the configured credential and permissions.')
            if response.status_code != 200:
                return outcome('unavailable', f'Metadata request returned HTTP {response.status_code}. Retry after checking the provider.')
            content = bytearray()
            # Small chunks enforce the elapsed limit even with a slowly trickling server.
            for chunk in response.iter_content(chunk_size=1):
                content.extend(chunk)
                if len(content) > 256 * 1024 or time.monotonic() - started > 4:
                    return outcome('unverified', 'Metadata response exceeded the size or time limit.')
            payload = json.loads(content)
        rows = payload.get('models' if provider in {'ollama','gemini'} else 'data')
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            return outcome('unverified', 'Endpoint returned an unsupported metadata format.')
        identifiers = {row.get('name', row.get('model')) if provider in {'ollama','gemini'} else row.get('id') for row in rows}
        if any(not isinstance(value, str) or not value for value in identifiers):
            return outcome('unverified', 'Endpoint returned invalid model identifiers.')
        wanted = {model, model + ':latest'} if provider == 'ollama' and ':' not in model else {model}
        if provider == 'gemini':
            wanted.add('models/' + model.removeprefix('models/'))
        if not wanted & identifiers:
            if payload.get('has_more') or payload.get('next_cursor') or payload.get('nextPageToken'):
                return outcome('unverified', 'Model not found on the returned metadata page; listing is incomplete.')
            return outcome('missing_model', 'Configured model is absent from the returned model list. Check its name or install it explicitly.', model_available=False)
        return outcome('reachable', 'Configured model is listed. Inference has not been tested.', healthy=True, model_available=True)
    except requests.Timeout:
        return outcome('unavailable', 'Metadata check timed out. Check the endpoint and retry.', reachable=False)
    except requests.RequestException:
        return outcome('unavailable', 'Metadata endpoint could not be reached. Check the service and endpoint.', reachable=False)
    except (ValueError, TypeError):
        return outcome('unverified', 'Endpoint returned invalid model metadata.')


def disk_readiness(paths, *, warning_bytes=2 * 1024**3, critical_bytes=512 * 1024**2):
    paths = {name: str(Path(path).resolve()) for name, path in paths.items()}
    key = (tuple(sorted(paths.items())), warning_bytes, critical_bytes)
    return DISK_CACHE.get(key, lambda: _disk_readiness(paths, warning_bytes, critical_bytes))


def _disk_readiness(paths, warning_bytes, critical_bytes):
    areas = []
    for name, path in paths.items():
        row = dict(name=name, path=path, state='unavailable', writable=False, free_bytes=None)
        try:
            stat = os.statvfs(path)
            row['free_bytes'] = stat.f_bavail * stat.f_frsize
            row['total_bytes'] = stat.f_blocks * stat.f_frsize
            row['free_inodes'] = stat.f_favail
            with tempfile.NamedTemporaryFile(prefix='.crowdlens-write-check-', dir=path) as handle:
                handle.write(b'readiness\n')
                handle.flush()
                os.fsync(handle.fileno())
            row['writable'] = True
            if row['free_bytes'] < critical_bytes or (stat.f_files > 0 and stat.f_favail == 0):
                row.update(state='critical', message='Storage is nearly full. Free space before starting work.')
            elif row['free_bytes'] < warning_bytes:
                row.update(state='warning', message='Storage space is low. Free space before a larger run.')
            else:
                row.update(state='ready', message='Storage write check passed.')
        except OSError as exc:
            row.update(message='Storage write check failed. Check that the directory exists, its permissions and free space.', errno=exc.errno)
        areas.append(row)
    states = {row['state'] for row in areas}
    state = 'unavailable' if 'unavailable' in states else 'critical' if 'critical' in states else 'warning' if 'warning' in states else 'ready'
    return dict(state=state, healthy=state in {'ready', 'warning'}, areas=areas,
                warning_bytes=warning_bytes, critical_bytes=critical_bytes)
