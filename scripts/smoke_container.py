#!/usr/bin/env python3
"""Offline production-image smoke: no ports, external network or real data."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    name = 'crowdlens-smoke-' + uuid.uuid4().hex[:12]
    volume = name + '-data'
    receipt = {'image': args.image, 'revision': args.revision, 'network': 'none'}
    probe = '''
import json, re, urllib.request, urllib.error
get = lambda path, port=3000: urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=8)
health = json.load(get('/health', 5001))
status = json.load(get('/api/status'))['data']
assert health['build']['declared_revision'] == REVISION, health
assert status['control_db']['healthy'], status
assert status['healthy'] is False, 'External dependencies must be unavailable offline'
page = get('/').read().decode()
assert '/@vite/client' not in page and 'CrowdLens' in page, page[:500]
asset = re.search(r'src="(/assets/[^" ]+\\.js)"', page).group(1)
assert 'immutable' in get(asset).headers['Cache-Control']
assert get('/report/synthetic-history-route').read().decode() == page
for path in ('/api/does-not-exist', '/assets/missing.js', '/.env'):
    try: get(path)
    except urllib.error.HTTPError as error: assert error.code == 404
    else: raise AssertionError(path + ' should not return the SPA')
print(json.dumps({'build': health['build'], 'asset': asset, 'control_db_healthy': True}))
'''.replace('REVISION', repr(args.revision))
    try:
        details = json.loads(docker('image', 'inspect', args.image))[0]
        assert details['Config']['Labels']['org.opencontainers.image.revision'] == args.revision
        assert details['Config']['User'] not in ('', '0', 'root', '0:0')
        receipt['image_id'] = details['Id']
        docker('volume', 'create', volume)
        docker('run', '--detach', '--name', name, '--network', 'none',
               '--mount', f'type=volume,src={volume},dst=/app/backend/uploads',
               '-e', 'LLM_API_KEY=offline-smoke-only', '-e', 'LLM_BASE_URL=http://127.0.0.1:9/v1',
               '-e', 'NEO4J_URI=bolt://127.0.0.1:9', '-e', 'NEO4J_PASSWORD=offline-smoke-only',
               '-e', 'STARTUP_STATUS_CHECK=False', '-e', 'EMBEDDING_AUTO_PULL=False', args.image)
        for _ in range(90):
            check = subprocess.run(['docker', 'exec', name, 'python', '-c',
                                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/health',timeout=2)"],
                                   capture_output=True)
            if check.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Image did not start within 90 seconds')
        receipt['first_start'] = json.loads(docker('exec', name, 'python', '-c', probe))
        docker('exec', name, 'python', '-c', '''
import sqlite3
from pathlib import Path
with sqlite3.connect('/app/backend/uploads/mirofish.db') as db:
    db.execute('CREATE TABLE smoke_sentinel (value TEXT)')
    db.execute("INSERT INTO smoke_sentinel VALUES ('retained')")
Path('/app/backend/uploads/smoke-artifact.txt').write_text('retained')
''')
        docker('stop', '--timeout', '60', name)
        stopped = json.loads(docker('inspect', name))[0]['State']
        assert stopped['ExitCode'] == 0 and not stopped['OOMKilled'], stopped
        docker('start', name)
        for _ in range(90):
            check = subprocess.run(['docker', 'exec', name, 'python', '-c', probe], capture_output=True, text=True)
            if check.returncode == 0:
                receipt['restart'] = json.loads(check.stdout)
                break
            time.sleep(1)
        else:
            raise RuntimeError('Image did not recover after restart: ' + check.stderr[-2000:])
        docker('exec', name, 'python', '-c', '''
import sqlite3
from pathlib import Path
with sqlite3.connect('/app/backend/uploads/mirofish.db') as db:
    assert db.execute('SELECT value FROM smoke_sentinel').fetchone() == ('retained',)
assert Path('/app/backend/uploads/smoke-artifact.txt').read_text() == 'retained'
''')
        receipt.update(result='passed', nonroot=True, graceful_shutdown=True, persisted_after_restart=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt, indent=2))
    except Exception:
        subprocess.run(['docker', 'logs', '--tail', '80', name])
        raise
    finally:
        subprocess.run(['docker', 'rm', '--force', name], capture_output=True)
        subprocess.run(['docker', 'volume', 'rm', volume], capture_output=True)


if __name__ == '__main__':
    main()
