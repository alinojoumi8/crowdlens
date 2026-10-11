from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest
from flask import Flask

from app.frontend import install_frontend


@pytest.fixture
def client(tmp_path):
    (tmp_path / 'index.html').write_text('<html>CrowdLens</html>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets/app-Abcd1234.js').write_text('const loaded = true;')
    (tmp_path / 'icon.svg').write_text('<svg/>')
    (tmp_path / '.env').write_text('SECRET=hidden')
    app = Flask(__name__)
    app.get('/api/status')(lambda: {'status': 'ok'})
    install_frontend(app, tmp_path)
    return app.test_client()


@pytest.mark.parametrize('path', ['/', '/report/example', '/cases/example'])
def test_history_routes_use_uncached_index(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b'CrowdLens' in response.data
    assert response.headers['Cache-Control'] == 'no-cache'


@pytest.mark.parametrize('path', ['/api/missing', '/health/missing', '/assets/missing.js',
                                  '/missing.svg', '/.env', '/%2e%2e/.env'])
def test_missing_api_assets_and_hidden_files_do_not_return_spa(client, path):
    assert client.get(path).status_code == 404


def test_assets_have_correct_cache_and_api_is_preserved(client):
    assert client.get('/api/status').json == {'status': 'ok'}
    assert 'immutable' in client.get('/assets/app-Abcd1234.js').headers['Cache-Control']
    assert client.get('/icon.svg').headers['Cache-Control'] == 'no-cache'


def test_missing_build_fails_startup(tmp_path):
    with pytest.raises(RuntimeError, match='npm run build'):
        install_frontend(Flask(__name__), tmp_path)


@pytest.mark.parametrize('overrides', [{'workers': 2}, {'preload_app': True}, {'max_requests': 100}])
def test_server_rejects_settings_that_lose_task_ownership(overrides):
    config = runpy.run_path(str(Path(__file__).parents[1] / 'gunicorn.conf.py'))
    settings = dict(workers=1, preload_app=False, max_requests=0)
    config['on_starting'](SimpleNamespace(cfg=SimpleNamespace(**settings)))
    settings.update(overrides)
    with pytest.raises(RuntimeError, match='one worker'):
        config['on_starting'](SimpleNamespace(cfg=SimpleNamespace(**settings)))
