"""Backup LLM for when the main provider is rate limited or out of quota.

Set LLM_FALLBACK_API_KEY, LLM_FALLBACK_BASE_URL and LLM_FALLBACK_MODEL_NAME
(OpenAI-compatible, for example OpenRouter) to enable it. A workflow can use
the backup only if its authorization names it.
"""
import os
import threading
import time

LIMIT_STATUSES = {429, 503, 529}
LIMIT_WORDS = ('rate limit', 'rate_limit', 'too many requests', 'quota',
               'usage limit', 'insufficient balance', 'insufficient_balance')

_lock = threading.Lock()
_limited_until = {}


def fallback_settings():
    """Return the backup provider, or None when it is not fully configured."""
    api_key = os.environ.get('LLM_FALLBACK_API_KEY', '').strip()
    base_url = os.environ.get('LLM_FALLBACK_BASE_URL', '').strip()
    model = os.environ.get('LLM_FALLBACK_MODEL_NAME', '').strip()
    if not (api_key and base_url and model):
        return None
    provider = os.environ.get('LLM_FALLBACK_PROVIDER', '').strip() or 'openrouter'
    return dict(provider=provider, api_key=api_key, base_url=base_url, model=model)


def same_endpoint(model_a, url_a, model_b, url_b):
    """True when two model/address pairs name the same model at the same endpoint."""
    from ..services.workflow_execution import endpoint_identity
    return model_a == model_b and endpoint_identity(url_a) == endpoint_identity(url_b)


def usable_backup(settings):
    """True when the current workflow authorized this backup."""
    from ..services.workflow_execution import scope_authorizes
    return bool(settings) and scope_authorizes(settings['model'], settings['base_url'])


def is_limit_error(exc):
    """True when the provider refused the call for rate or quota reasons."""
    response = getattr(exc, 'response', None)
    status = getattr(exc, 'status_code', None) or getattr(response, 'status_code', None)
    if status in LIMIT_STATUSES:
        return True
    if not status or status < 400:
        return False
    try:
        text = (response.text or '').lower()
    except Exception:
        text = ''
    return any(word in text for word in LIMIT_WORDS)


def _cooldown_seconds():
    try:
        return max(0.0, float(os.environ.get('LLM_FALLBACK_COOLDOWN_SECONDS', '300')))
    except ValueError:
        return 300.0


def _key(model, base_url):
    from ..services.workflow_execution import endpoint_identity
    return model, endpoint_identity(base_url)


def mark_primary_limited(model, base_url):
    """Send this main model's calls to the backup for a while, so each call does not wait on retries."""
    with _lock:
        _limited_until[_key(model, base_url)] = time.monotonic() + _cooldown_seconds()


def primary_limited(model, base_url):
    with _lock:
        return time.monotonic() < _limited_until.get(_key(model, base_url), 0.0)


def reset():
    with _lock:
        _limited_until.clear()
