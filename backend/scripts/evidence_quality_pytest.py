"""Network guard for the explicitly local evidence-quality pytest invocation."""
import socket
import pytest


@pytest.fixture(autouse=True)
def evidence_quality_no_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError('evidence_quality_network_forbidden')
    monkeypatch.setattr(socket.socket, 'connect', refused)
    monkeypatch.setattr(socket.socket, 'connect_ex', refused)
    monkeypatch.setattr(socket, 'create_connection', refused)
