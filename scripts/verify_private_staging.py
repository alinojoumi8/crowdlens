#!/usr/bin/env python3
"""Verify an owned fictional staging release, retaining data and private receipts."""
import argparse
import http.client
import json
from pathlib import Path
import re
import socket
import ssl
import time
import uuid

from private_staging import HOST, command, compose, container, export_ca, load_release, sha256


def inspect(state, service):
    return json.loads(command(['docker', 'inspect', container(state, service)]))[0]


def request(release, context, path='/', headers=None):
    conn = http.client.HTTPSConnection(HOST, release['https_port'], context=context, timeout=10)
    try:
        # A fixed loopback route avoids host DNS edits; SNI and hostname checks remain enabled.
        conn.sock = context.wrap_socket(socket.create_connection(('127.0.0.1', release['https_port']),
                                                                  timeout=10), server_hostname=HOST)
        cert = conn.sock.getpeercert()
        conn.request('GET', path, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read(), cert
    finally:
        conn.close()


def confinement(state, release):
    app, proxy = inspect(state, 'app'), inspect(state, 'proxy')
    assert app['Image'] == release['image'], 'Running app image changed'
    assert proxy['Image'] == release['proxy_image'], 'Running proxy image changed'
    for obj in (app, proxy):
        assert obj['Config']['User'] == '1000:1000'
        assert obj['HostConfig']['ReadonlyRootfs']
        assert obj['HostConfig']['CapDrop'] == ['ALL']
        assert obj['HostConfig']['Memory'] > 0 and obj['HostConfig']['NanoCpus'] > 0
        assert obj['HostConfig']['PidsLimit'] > 0
    assert not app['HostConfig']['PortBindings'], 'Backend ports must not be published'
    assert len(app['NetworkSettings']['Networks']) == 1
    network = next(iter(app['NetworkSettings']['Networks']))
    assert network == release['project'] + '_application'
    assert json.loads(command(['docker', 'network', 'inspect', network]))[0]['Internal'] is True
    ports = proxy['HostConfig']['PortBindings']
    assert set(ports) == {str(release['https_port']) + '/tcp', str(release['http_port']) + '/tcp'}
    assert all(v == [{'HostIp': '127.0.0.1', 'HostPort': k.split('/')[0]}] for k, v in ports.items())
    for obj in (app, proxy):
        for mount in obj['Mounts']:
            if mount['Type'] == 'volume':
                assert mount['Name'].startswith(release['project'] + '_')
            else:
                assert obj is proxy and mount['Destination'] == '/etc/caddy/Caddyfile'
                assert Path(mount['Source']).resolve() == (state / 'Caddyfile').resolve() and not mount['RW']
    env = dict(v.split('=', 1) for v in app['Config']['Env'])
    assert env['AUTH_MODE'] == 'local' and env['LLM_BASE_URL'] == 'http://127.0.0.1:9/v1'
    assert env['LLM_API_KEY'] == 'fictional-offline-only' and env['NEO4J_URI'] == 'bolt://127.0.0.1:9'
    assert env['EMBEDDING_AUTO_PULL'] == 'False'
    return app, proxy


def fixture(state, token, create=False):
    # A distinct fixture row/file per run: no existing application rows are changed.
    script = '''
import json, sqlite3
from pathlib import Path
token = __TOKEN__
path = Path('/app/backend/uploads/staging-fixture-' + token + '.txt')
with sqlite3.connect('/app/backend/uploads/mirofish.db') as db:
    if __CREATE__:
        db.execute('CREATE TABLE IF NOT EXISTS staging_fixture (id TEXT PRIMARY KEY, value TEXT)')
        db.execute('INSERT INTO staging_fixture VALUES (?, ?)', (token, 'fictional-only'))
        path.write_text('fictional-only')
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='staging_fixture'").fetchone()
    row = db.execute('SELECT value FROM staging_fixture WHERE id=?', (token,)).fetchone() if exists else None
print(json.dumps({'file': path.is_file(), 'row': row}))
'''.replace('__TOKEN__', repr(token)).replace('__CREATE__', repr(create))
    return json.loads(command(['docker', 'exec', container(state, 'app'), 'python', '-c', script]))


def runtime_identity(state):
    return json.loads(command(['docker', 'exec', container(state, 'app'), 'python', '-c',
        "import json,urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:3000/health'))['build']))"]))


def verify(state, peer_state=None, wait_renewal=0):
    if not __debug__:
        raise RuntimeError('Verification requires Python without optimization')
    release = load_release(state)
    app, proxy = confinement(state, release)
    ca = export_ca(state)
    root_hash = sha256(ca)
    context = ssl.create_default_context(cafile=str(ca))
    # A private CA must not become implicitly trusted by the host.
    try:
        request(release, ssl.create_default_context())
    except ssl.SSLCertVerificationError:
        pass
    else:
        raise AssertionError('A new private CA unexpectedly has system trust')
    try:
        with socket.create_connection(('127.0.0.1', release['https_port']), timeout=5) as raw:
            with context.wrap_socket(raw, server_hostname='unrelated.invalid'):
                pass
    except ssl.SSLError:
        pass
    else:
        raise AssertionError('Wrong TLS hostname accepted')
    status, headers, body, first_cert = request(release, context)
    assert status == 200 and b'CrowdLens' in body and b'/@vite/client' not in body
    assert headers.get('Strict-Transport-Security') == 'max-age=86400'
    assert 'Content-Security-Policy' in headers and 'Server' not in headers
    asset = re.search(rb'src="(/assets/[^" ]+\.js)"', body)[1].decode()
    assert request(release, context, asset)[0] == 200
    assert 'immutable' in request(release, context, asset)[1]['Cache-Control']
    assert request(release, context, '/report/fictional-history')[2] == body
    for path in ['/.env', '/.git/config', '/health', '/assets/missing.js', '/api/does-not-exist']:
        assert request(release, context, path)[0] == 404, path
    assert request(release, context, '/api/status', {'Origin': 'https://unrelated.invalid'})[0] == 403
    assert request(release, context, '/', {'Host': 'unrelated.invalid'})[0] >= 400
    conn = http.client.HTTPConnection('127.0.0.1', release['http_port'], timeout=10)
    conn.request('GET', '/fictional?test=1', headers={'Host': f'{HOST}:{release["http_port"]}'})
    response = conn.getresponse()
    assert response.status == 308 and response.getheader('Location') == release['url'] + '/fictional?test=1'
    response.read(); conn.close()
    status, _, payload, _ = request(release, context, '/api/status')
    data = json.loads(payload)['data']
    assert status == 200 and data['control_db']['healthy'] is True
    assert data['healthy'] is False, 'Provider-disabled staging must report unavailable dependencies'
    health = runtime_identity(state)
    assert health == release['source'], 'Runtime source identity differs from the release record'
    token = uuid.uuid4().hex
    expected_fixture = {'file': True, 'row': ['fictional-only']}
    assert fixture(state, token, create=True) == expected_fixture
    receipt = {'release': release['project'], 'revision': release['revision'], 'image': app['Image'],
               'proxy_image': proxy['Image'], 'build': health, 'asset': asset, 'url': release['url'],
               'tls': 'verified_private_ca_and_hostname', 'root_ca_sha256': root_hash,
               'provider_dependencies': 'intentionally_unavailable', 'second_device': 'deferred_by_user'}
    if peer_state is not None:
        peer = load_release(peer_state)
        peer_app, peer_proxy = confinement(peer_state, peer)
        assert peer['project'] != release['project']
        ours = {m['Name'] for obj in (app, proxy) for m in obj['Mounts'] if m['Type'] == 'volume'}
        theirs = {m['Name'] for obj in (peer_app, peer_proxy) for m in obj['Mounts'] if m['Type'] == 'volume'}
        assert not ours.intersection(theirs)
        assert fixture(peer_state, token) == {'file': False, 'row': None}
        assert sha256(export_ca(peer_state)) != root_hash
        secret = lambda obj: next(v for v in obj['Config']['Env'] if v.startswith('SECRET_KEY='))
        assert secret(app) != secret(peer_app)
        receipt['peer_isolation'] = 'separate_volumes_credentials_ca_and_fixture_data'
    if wait_renewal:
        deadline = time.monotonic() + wait_renewal
        while time.monotonic() < deadline:
            renewed = request(release, context)[3]
            if renewed['serialNumber'] != first_cert['serialNumber']:
                assert ssl.cert_time_to_seconds(renewed['notAfter']) > ssl.cert_time_to_seconds(first_cert['notAfter'])
                receipt['renewal'] = {'result': 'passed', 'before': first_cert['serialNumber'],
                                      'after': renewed['serialNumber']}
                break
            time.sleep(3)
        else:
            raise AssertionError('No automatic certificate renewal observed in the specified window')
    compose(state, 'stop')
    for obj in (app, proxy):
        stopped = json.loads(command(['docker', 'inspect', obj['Id']]))[0]['State']
        assert stopped['ExitCode'] == 0 and not stopped['OOMKilled']
    compose(state, 'up', '--detach', '--wait', '--wait-timeout', '120')
    assert fixture(state, token) == expected_fixture
    assert sha256(export_ca(state)) == root_hash
    assert request(release, context)[0] == 200
    receipt['restart_build'] = runtime_identity(state)
    assert receipt['restart_build'] == health
    confinement(state, release)
    receipt.update(result='passed', graceful_shutdown=True, persisted_after_restart=True)
    (state / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--peer-state', type=Path)
    parser.add_argument('--wait-renewal', type=int, default=0,
                        help='Seconds to observe a short-lived disposable renewal rehearsal')
    args = parser.parse_args()
    print(json.dumps(verify(args.state.resolve(), args.peer_state.resolve() if args.peer_state else None,
                            args.wait_renewal), indent=2))
