"""Render the real override: unsafe base/ambient settings must not retain ports."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def render(tmp_path, *, unsafe_base=False, gpu=False):
    base = (ROOT / 'docker-compose.yml').read_text()
    if unsafe_base:
        base = base.replace('127.0.0.1:', '0.0.0.0:')
        base = base.replace('    ports:\n', '    ports:\n      - "0.0.0.0:29999:29999"\n')
    (tmp_path / 'docker-compose.yml').write_text(base)
    (tmp_path / '.env').write_text('NEO4J_PASSWORD=fictional-test-only\n')
    command = ['docker', 'compose', '--project-name', 'mirofish-local',
               '--project-directory', str(tmp_path), '--env-file', str(tmp_path / '.env'),
               '-f', str(tmp_path / 'docker-compose.yml')]
    if gpu:
        command += ['-f', str(ROOT / 'docker-compose.gpu.yml')]
    command += ['-f', str(ROOT / 'deploy/private-network/compose.yaml'),
                'config', '--format', 'json']
    env = {'PATH': os.environ['PATH'], 'HOME': os.environ.get('HOME', str(tmp_path)),
           'NEO4J_IMAGE': 'neo4j:latest', 'OLLAMA_IMAGE': 'ollama/ollama:latest'}
    return json.loads(subprocess.check_output(command, text=True, env=env, timeout=30))


@pytest.mark.skipif(not shutil.which('docker'), reason='Docker Compose CLI unavailable')
@pytest.mark.parametrize('unsafe_base', [False, True])
@pytest.mark.parametrize('gpu', [False, True])
def test_private_override_replaces_ports_pins_images_and_preserves_consumers(tmp_path, unsafe_base, gpu):
    config = render(tmp_path, unsafe_base=unsafe_base, gpu=gpu)
    services = config['services']
    expected = {'mirofish': {3000, 5001}, 'neo4j': {7474, 7687}, 'ollama': {11434}}
    for name, ports in expected.items():
        actual = services[name]['ports']
        assert {int(p['published']) for p in actual} == ports
        assert all(p['host_ip'] == '127.0.0.1' and int(p['published']) == p['target'] for p in actual)
        assert services[name]['pull_policy'] == 'never'
    assert not services['mirofish'].get('build')
    assert services['mirofish']['image'] == 'sha256:6b28dd78e5fe4b1b21a2879d612f519f8229a84c31f9ea56315504fb0f6bfe7e'
    assert services['neo4j']['image'].endswith('@sha256:8f01f7bb053e5564eb84a3f1824e4ca2202d29dd415d196cf8e27c8f7e6b611e')
    assert services['ollama']['image'].endswith('@sha256:a6149234667efc71d37766d61c1a16f24c33e4cd7a0bf4125c44a7e47e2419c4')
    assert set(services['mirofish']['networks']) == {'default', 'dependencies'}
    assert set(services['neo4j']['networks']) == set(services['ollama']['networks']) == {'dependencies'}
    assert config['networks']['default']['name'] == 'mirofish-local_default'
    assert config['networks']['dependencies']['driver_opts']['com.docker.network.bridge.host_binding_ipv4'] == '127.0.0.1'
    assert config['networks']['dependencies'].get('internal', False) is False
    assert services['mirofish']['environment']['NEO4J_URI'] == 'bolt://neo4j:7687'
    assert services['mirofish']['environment']['EMBEDDING_BASE_URL'] == 'http://ollama:11434'
    assert services['neo4j']['container_name'] == 'mirofish-neo4j'
    assert services['ollama']['container_name'] == 'mirofish-ollama'
    assert config['volumes']['neo4j_data']['name'] == 'mirofish-local_neo4j_data'
    assert config['volumes']['neo4j_logs']['name'] == 'mirofish-local_neo4j_logs'
    assert config['volumes']['ollama_data']['name'] == 'mirofish-local_ollama_data'
    if gpu:
        assert services['ollama']['deploy']['resources']['reservations']['devices'][0]['capabilities'] == ['gpu']
