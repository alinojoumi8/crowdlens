from flask import Flask

def test_status_has_nonsecret_source_identity():
    from app.api import status_bp
    app = Flask(__name__); app.register_blueprint(status_bp, url_prefix='/api')
    data = app.test_client().get('/api/status').json['data']['build']
    assert set(data) == {'declared_revision', 'source_sha256', 'scope'}
    assert len(data['source_sha256']) == 64


def test_identity_ignores_private_data_and_changes_with_source(tmp_path):
    from app.utils.build_identity import source_identity
    (tmp_path/'backend/app').mkdir(parents=True)
    source = tmp_path/'backend/app/example.py'; source.write_text('value = 1')
    a = source_identity(tmp_path, revision='not-a-revision secret')
    (tmp_path/'.env').write_text('PRIVATE=value')
    (tmp_path/'backend/uploads').mkdir()
    (tmp_path/'backend/uploads/private.txt').write_text('private synthetic data')
    assert source_identity(tmp_path) == a
    assert a['declared_revision'] is None
    source.write_text('value = 2')
    assert source_identity(tmp_path)['source_sha256'] != a['source_sha256']
    assert source_identity(tmp_path, revision='a'*40)['declared_revision'] == 'a'*40
