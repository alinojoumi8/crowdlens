"""Unit tests are offline regardless of an operator's local rollout flags."""
import pytest


@pytest.fixture(autouse=True)
def disable_live_jev(monkeypatch):
    from app.config import Config
    for name in ('JEV_INTERVIEW_MODE', 'JEV_RERANK_MODE', 'JEV_EVIDENCE_MODE'):
        monkeypatch.setattr(Config, name, 'off')
