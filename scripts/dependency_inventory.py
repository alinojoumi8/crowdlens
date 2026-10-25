#!/usr/bin/env python3
"""Read-only, endpoint-only inventory for the B11 dependency change review.

Does not query databases, run inference, read source documents or print env values.
Configuration hints and visible process environments are not exhaustive discovery.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


TARGETS = {'mirofish-neo4j', 'mirofish-ollama'}
PORTS = {7474, 7687, 7688, 7690, 11434, 8010, 8011}
ENDPOINT_KEYS = {
    'NEO4J_URI', 'NEO4J_URL', 'OLLAMA_HOST', 'OLLAMA_URL', 'OLLAMA_BASE_URL',
    'OLLAMA_API_URL', 'EMBEDDING_BASE_URL', 'EMBEDDING_API_URL',
    'OPENAI_API_BASE_URL', 'OPENAI_BASE_URL', 'LLM_BASE_URL', 'GRAPHITI_BRIDGE_URL',
}
SENSITIVE = re.compile(r'password|secret|token|key', re.I)
ASSIGNMENT = re.compile(r'^\s*(?:export\s+)?[\"\']?([\w.-]+)[\"\']?\s*[:=]\s*(.*)')
URL = re.compile(r'(?:https?|bolt|neo4j)(?:\+s|\+ssc)?://[^\s\"\'{}<>]+')


def command(args):
    return subprocess.check_output(args, text=True, timeout=30, stderr=subprocess.PIPE)


def endpoint(value):
    """Return only a protocol/host/port, never credentials, paths or query data."""
    try:
        parsed = urlsplit(value if '://' in value else 'http://' + value)
        if (parsed.scheme in {'http', 'https', 'bolt', 'bolt+s', 'bolt+ssc', 'neo4j', 'neo4j+s', 'neo4j+ssc'}
                and parsed.port in PORTS and parsed.hostname):
            return {'scheme': parsed.scheme, 'host': parsed.hostname, 'port': parsed.port}
    except ValueError:
        pass
    return None


def environment_endpoints(values):
    result = {}
    for item in values:
        key, separator, value = item.partition('=')
        if separator and key in ENDPOINT_KEYS:
            safe = endpoint(value)
            if safe:
                result[key] = safe
    return result


def configuration_hints(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Select a regular configuration file')
    with path.open('rb') as source:
        content = source.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024:
        raise ValueError('Configuration inventory is limited to 1 MiB per file')
    hints = []
    for number, line in enumerate(content.decode().splitlines(), 1):
        match = ASSIGNMENT.match(line)
        if not match or SENSITIVE.search(match[1]):
            continue
        for value in URL.findall(match[2]):
            safe = endpoint(value)
            if safe:
                hints.append({'line': number, 'key': match[1], 'endpoint': safe})
    return {'file': str(path), 'hints': hints, 'evidence': 'configuration_only'}


def container_record(obj):
    labels = obj['Config'].get('Labels') or {}
    return {
        'name': obj['Name'].lstrip('/'), 'running': obj['State']['Running'],
        'image_reference': obj['Config']['Image'], 'image_id': obj['Image'],
        'compose_project': labels.get('com.docker.compose.project'),
        'endpoints': environment_endpoints(obj['Config'].get('Env') or []),
        'networks': sorted(obj['NetworkSettings']['Networks']),
        'published_ports': obj['HostConfig'].get('PortBindings') or {},
        'volumes': [{'name': m.get('Name'), 'destination': m['Destination'], 'type': m['Type']}
                    for m in obj.get('Mounts', [])],
    }


def process_inventory(proc=Path('/proc')):
    result, inaccessible = [], 0
    for path in proc.iterdir():
        if not path.name.isdecimal():
            continue
        try:
            values = path.joinpath('environ').read_bytes().decode(errors='replace').split('\0')
            endpoints = environment_endpoints(values)
            if endpoints:
                result.append({'pid': int(path.name), 'process': path.joinpath('comm').read_text().strip(),
                               'endpoints': endpoints})
        except PermissionError:
            inaccessible += 1
        except (FileNotFoundError, ProcessLookupError):
            pass
    return {'visible_endpoint_processes': result, 'inaccessible_processes': inaccessible,
            'evidence': 'environment_only_not_proof_of_active_connection'}


def version_requirement(value, minimum):
    value = value.strip().removeprefix('v')
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:\+[A-Za-z0-9.-]+)?', value)
    return {'version': value if match else 'unrecognized',
            'supported': bool(match and tuple(map(int, match.groups())) >= minimum)}


def collect(paths):
    ids = command(['docker', 'ps', '--all', '--quiet']).split()
    objects = json.loads(command(['docker', 'inspect', *ids])) if ids else []
    targets, consumers = [], []
    for obj in objects:
        record = container_record(obj)
        if record['name'] in TARGETS:
            image = json.loads(command(['docker', 'image', 'inspect', obj['Image']]))[0]
            record['repo_digests'] = image.get('RepoDigests') or []
            targets.append(record)
        elif record['endpoints']:
            # Includes stopped consumers: a rollback/restart may use them later.
            consumers.append(record)
    return {
        'collected_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'local Docker metadata, readable process environments, explicitly supplied configuration files',
        'targets': targets, 'container_endpoint_candidates': consumers,
        'missing_targets': sorted(TARGETS - {t['name'] for t in targets}),
        'private_network_prerequisites': {
            'engine_28_or_newer': version_requirement(command(['docker', 'version', '--format', '{{.Server.Version}}']), (28, 0, 0)),
            'compose_2_24_4_or_newer': version_requirement(command(['docker', 'compose', 'version', '--short']), (2, 24, 4)),
        },
        'host_processes': process_inventory(),
        'configuration_hints': [configuration_hints(p) for p in paths],
        'limits': ['Endpoint candidates require network/owner confirmation.',
                   'Unreadable processes, code defaults, dynamic configuration and remote consumers may be absent.',
                   'No database, model, HTTP, firewall, service or credential changes were performed.'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, action='append', default=[],
                        help='Explicit env/YAML/TOML configuration to inspect for endpoint hints only')
    args = parser.parse_args()
    try:
        report = collect(args.config)
        print(json.dumps(report, indent=2))
        if report['missing_targets'] or not all(v['supported'] for v in report['private_network_prerequisites'].values()):
            parser.exit(2, 'Private-network preflight requires both target containers, Engine >= 28.0.0 and Compose >= 2.24.4. Do not recreate services.\n')
    except (OSError, ValueError, subprocess.SubprocessError):
        # Exception strings can contain source content. Do not echo them.
        raise SystemExit('Inventory failed; check Docker access and supplied configuration paths.') from None
