"""The consumer inventory must not serialize credentials or private source text."""
import importlib.util
import json
from pathlib import Path
import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('dependency_inventory', ROOT / 'scripts/dependency_inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


@pytest.mark.parametrize('url', [
    'bolt://user:private-password@localhost:7687/private-db?token=private-token#private-fragment',
    'http://user:private-password@localhost:7687/private-path?token=private-token',
])
def test_endpoint_only_redaction(url):
    result = inventory.endpoint(url)
    assert result['host'] == 'localhost' and result['port'] == 7687
    assert set(result) == {'scheme', 'host', 'port'}
    assert 'private-' not in json.dumps(result)


@pytest.mark.parametrize('url', ['http://host:invalid', 'http://[broken', 'https://api.example.test/v1', 'http://localhost:9',
                                 'file://localhost:7687/private'])
def test_invalid_or_unrelated_endpoint_is_not_a_consumer(url):
    assert inventory.endpoint(url) is None


def test_environment_ignores_sensitive_keys_and_arbitrary_values():
    result = inventory.environment_endpoints([
        'NEO4J_URI=bolt://user:secret@localhost:7687/db?password=secret',
        'API_KEY=http://localhost:11434/private', 'PROMPT=http://localhost:11434/private',
        'PASSWORD=private', 'BROKEN',
    ])
    assert list(result) == ['NEO4J_URI']
    assert 'secret' not in json.dumps(result)


def test_configuration_hints_do_not_include_secret_fields_comments_or_paths(tmp_path):
    path = tmp_path / 'fictional.env'
    path.write_text('# NEO4J_URI=bolt://private:private@localhost:7687\n'
                    'NEO4J_URI="bolt://user:private@localhost:7687/private?token=private"\n'
                    'api_key: http://localhost:11434/private\n'
                    'api_url: http://localhost:11434/private\n')
    result = inventory.configuration_hints(path)
    assert [r['key'] for r in result['hints']] == ['NEO4J_URI', 'api_url']
    assert all(set(r['endpoint']) == {'scheme', 'host', 'port'} for r in result['hints'])
    assert result['evidence'] == 'configuration_only'


def test_large_configuration_is_refused(tmp_path):
    path = tmp_path / 'large.env'
    path.write_bytes(b'x' * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match='1 MiB'):
        inventory.configuration_hints(path)


def test_special_configuration_input_is_refused(tmp_path):
    with pytest.raises(ValueError, match='regular'):
        inventory.configuration_hints(tmp_path)


def test_cli_does_not_echo_docker_error_payload(tmp_path):
    docker = tmp_path / 'docker'
    docker.write_text('#!/bin/sh\necho private-credential-sentinel >&2\nexit 1\n')
    docker.chmod(0o700)
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/dependency_inventory.py')],
                            text=True, capture_output=True, timeout=10,
                            env={**os.environ, 'PATH': str(tmp_path)})
    assert result.returncode != 0
    assert 'Inventory failed' in result.stderr
    assert 'private-credential-sentinel' not in result.stderr + result.stdout


def test_container_record_does_not_dump_environment_labels_or_bind_sources():
    obj = {'Name': '/fictional', 'State': {'Running': False}, 'Image': 'sha256:fictional',
           'Config': {'Image': 'fictional:old', 'Env': ['SECRET_KEY=never-print'],
                      'Labels': {'private': 'never-print', 'com.docker.compose.project': 'fixture'}},
           'NetworkSettings': {'Networks': {'fixture_default': {}}},
           'HostConfig': {'PortBindings': {}},
           'Mounts': [{'Type': 'bind', 'Source': '/private/never-print', 'Destination': '/data'}]}
    result = inventory.container_record(obj)
    assert not result['running'] and result['compose_project'] == 'fixture'
    assert 'never-print' not in json.dumps(result)


def test_process_environment_is_only_an_endpoint_hint(tmp_path):
    process = tmp_path / '123'
    process.mkdir()
    (process / 'environ').write_bytes(b'NEO4J_URI=bolt://user:secret@localhost:7687/db\0API_KEY=secret\0')
    (process / 'comm').write_text('fictional-python\n')
    result = inventory.process_inventory(tmp_path)
    assert result['visible_endpoint_processes'][0]['pid'] == 123
    assert result['evidence'] == 'environment_only_not_proof_of_active_connection'
    assert 'secret' not in json.dumps(result)


def test_missing_targets_are_explicit_in_an_empty_inventory(monkeypatch):
    monkeypatch.setattr(inventory, 'command', lambda args: '')
    monkeypatch.setattr(inventory, 'process_inventory', lambda: {'inaccessible_processes': 1})
    result = inventory.collect([])
    assert result['missing_targets'] == ['mirofish-neo4j', 'mirofish-ollama']
    assert result['host_processes']['inaccessible_processes'] == 1


@pytest.mark.parametrize('version,supported', [('27.5.1', False), ('28.0.0', True), ('29.8.1', True),
                                              ('28.0.0-rc1', False), ('invalid-private-sentinel', False)])
def test_loopback_version_gate_refuses_old_or_unrecognized_engines(version, supported):
    result = inventory.version_requirement(version, (28, 0, 0))
    assert result['supported'] is supported
    assert 'private-sentinel' not in json.dumps(result)


@pytest.mark.parametrize('version,supported', [('v2.24.3', False), ('v2.24.4', True), ('5.1.3', True)])
def test_compose_version_gate_requires_replacement_tag_support(version, supported):
    assert inventory.version_requirement(version, (2, 24, 4))['supported'] is supported
