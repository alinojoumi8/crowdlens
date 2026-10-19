"""Offline access-boundary and invitation/session regressions."""
import pytest
from flask import Flask


@pytest.fixture
def app(tmp_path):
    from app.authentication import install_authentication
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='test-secret-key-that-is-at-least-32-bytes',
        AUTH_MODE='oidc', AUTH_ALLOW_HTTP_LOOPBACK=True, AUTH_BASE_URL='http://localhost',
        AUTH_ISSUER='http://localhost:9999', AUTH_CLIENT_ID='test', AUTH_CLIENT_SECRET='secret',
        AUTH_ADMIN_EMAIL='admin@example.test', AUTH_DB_PATH=str(tmp_path / 'auth.db'))
    install_authentication(app)
    app.add_url_rule('/api/private', 'private', lambda: {'secret': True}, methods=['GET', 'POST'])
    app.add_url_rule('/api/report/private/download', 'download', lambda: 'private')
    app.add_url_rule('/health', 'health', lambda: {'status':'ok'})
    return app


def login(app, client, email='admin@example.test', sub='admin', invitation=None, amr=None):
    store = app.extensions['auth_store']
    user = store.admit({'iss':'http://localhost:9999','sub':sub,'email':email,
                       'email_verified':True,'amr':amr if amr is not None else ['mfa']}, invitation)
    token, csrf = store.new_session(user['id'])
    client.set_cookie('crowdlens_auth', token)
    return user, csrf


def test_anonymous_api_download_and_pages_are_protected(app):
    c=app.test_client()
    assert c.get('/api/private').status_code == 401
    assert c.get('/api/report/private/download').status_code == 401
    assert c.get('/').status_code == 302
    assert c.get('/health').status_code == 200


def test_admin_csrf_and_logout_revocation(app):
    c=app.test_client(); user,csrf=login(app,c)
    assert c.get('/api/private').status_code==200
    assert c.post('/api/private').status_code==403
    assert c.post('/api/private',headers={'X-CrowdLens-CSRF':csrf}).status_code==200
    token=c.get_cookie('crowdlens_auth').value
    assert c.post('/auth/logout',data={'csrf':csrf}).status_code==302
    c.set_cookie('crowdlens_auth',token)
    assert c.get('/api/private').status_code==401


def test_invite_single_use_email_binding_and_tester_boundary(app):
    admin=app.test_client();user,csrf=login(app,admin);store=app.extensions['auth_store']
    invite=store.invite('tester@example.test',user['id'])
    with pytest.raises(ValueError):
        store.admit({'iss':'http://localhost:9999','sub':'bad','email':'wrong@example.test','email_verified':True},invite)
    tester=app.test_client(); account,_=login(app,tester,'tester@example.test','tester',invite)
    assert account['role']=='tester'
    assert tester.get('/auth/account').status_code==200
    assert tester.get('/api/private').status_code==403
    assert tester.get('/api/report/private/download').status_code==403
    assert tester.post('/auth/invitations').status_code==403
    with pytest.raises(ValueError):
        login(app,app.test_client(),'tester@example.test','other',invite)


def test_unverified_identity_mfa_and_uninvited_rejected(app):
    store=app.extensions['auth_store']
    for claims in [dict(email='admin@example.test',email_verified=False,amr=['mfa']),
                   dict(email='admin@example.test',email_verified=True,amr=['pwd']),
                   dict(email='admin@example.test',email_verified=True,amr='not-mfa'),
                   dict(email='stranger@example.test',email_verified=True)]:
        with pytest.raises(ValueError):store.admit(dict(iss='http://localhost:9999',sub='x',**claims),None)


def test_expiry_suspend_and_revoke_all_sessions(app):
    c=app.test_client();admin,_=login(app,c);store=app.extensions['auth_store']
    t=app.test_client();invite=store.invite('tester@example.test',admin['id']);user,csrf=login(app,t,'tester@example.test','t',invite)
    store.suspend(user['id'],True,admin['id'])
    assert t.get('/auth/account').status_code==302
    with pytest.raises(ValueError):login(app,t,'tester@example.test','t')
    with pytest.raises(ValueError):store.suspend(admin['id'],True,admin['id'])


def test_invalid_configuration_fails_closed(tmp_path):
    from app.authentication import install_authentication
    a=Flask(__name__);a.config['AUTH_MODE']='typo'
    with pytest.raises(RuntimeError):install_authentication(a)
    a.config['AUTH_MODE']='oidc'
    with pytest.raises(RuntimeError):install_authentication(a)


def test_expired_invitation_and_sessions_fail(app, monkeypatch):
    from app.services import auth_store
    c=app.test_client();admin,_=login(app,c);store=app.extensions['auth_store']
    invite=store.invite('late@example.test',admin['id'])
    original=auth_store.time.time()
    monkeypatch.setattr(auth_store.time,'time',lambda:original+86401)
    with pytest.raises(ValueError):login(app,app.test_client(),'late@example.test','late',invite)
    assert c.get('/api/private').status_code==401


def test_idle_expiry_and_revoke_all(app, monkeypatch):
    from app.services import auth_store
    c=app.test_client();admin,_=login(app,c);store=app.extensions['auth_store']
    c2=app.test_client();login(app,c2)
    store.revoke_all(admin['id'])
    assert c.get('/api/private').status_code==401 and c2.get('/api/private').status_code==401
    login(app,c)
    original=auth_store.time.time()
    monkeypatch.setattr(auth_store.time,'time',lambda:original+1801)
    assert c.get('/api/private').status_code==401


def test_callback_state_replay_and_untrusted_identity(app, monkeypatch):
    c=app.test_client()
    assert c.get('/auth/callback?state=forged&code=x').status_code==400
    with c.session_transaction() as s:s['login_state']='bound'
    monkeypatch.setattr(app.extensions['auth_oidc'],'authorize_access_token',lambda:{'id_token':'bad','userinfo':{
        'iss':'https://attacker.invalid','sub':'admin','email':'admin@example.test','email_verified':True,'amr':['mfa']}})
    assert c.get('/auth/callback?state=bound&code=x').status_code==403
    assert c.get('/auth/callback?state=bound&code=x').status_code==400
    assert c.get('/api/private').status_code==401


def test_expired_form_and_cross_origin_mutation(app):
    c=app.test_client()
    assert c.post('/auth/start',data={'csrf':'invented'}).status_code==400
    _,csrf=login(app,c)
    assert c.post('/api/private',headers={'Origin':'https://evil.invalid','X-CrowdLens-CSRF':csrf}).status_code==403


@pytest.mark.parametrize('trailing_slash', [False, True])
def test_real_oidc_code_pkce_nonce_signature_and_recovery_browser(tmp_path, trailing_slash):
    """Actual signed JWT/network flow; provider recovery is simulated, not certified."""
    import re
    import threading
    import requests
    from pathlib import Path
    from werkzeug.serving import make_server
    from oidc_test_provider import start_provider
    from app.authentication import install_authentication
    provider, provider_server, issuer = start_provider(trailing_slash)
    a=Flask('oidc-integration');server=make_server('127.0.0.1',0,a,threaded=True)
    base=f'http://127.0.0.1:{server.server_port}'
    a.config.update(TESTING=True,SECRET_KEY='x'*40,AUTH_MODE='oidc',AUTH_ALLOW_HTTP_LOOPBACK=True,
        AUTH_BASE_URL=base,AUTH_ISSUER=issuer,AUTH_CLIENT_ID='fixture-client',AUTH_CLIENT_SECRET='fixture-secret',
        AUTH_ADMIN_EMAIL='admin@example.test',AUTH_DB_PATH=str(tmp_path/'auth.db'))
    install_authentication(a)
    a.add_url_rule('/api/private','private',lambda:{'ok':True})
    threading.Thread(target=server.serve_forever,daemon=True).start()
    def flow(browser,email='admin@example.test',invitation=''):
        html=browser.get(base+'/auth/signin').text
        csrf=re.search(r'name="csrf" value="([^"]+)"',html)[1]
        response=browser.post(base+'/auth/start',data={'csrf':csrf,'invitation':invitation})
        hidden=dict(re.findall(r'type="hidden" name="([^"]+)" value="([^"]*)"',response.text))
        import html as html_module
        hidden={k:html_module.unescape(v) for k,v in hidden.items()}
        return browser.post(issuer.rstrip('/')+'/authorize',data={**hidden,'email':email})
    try:
        first=requests.Session();assert flow(first).status_code==200
        assert first.get(base+'/api/private').status_code==200
        admin=a.extensions['auth_store'].accounts()[0]
        invite=a.extensions['auth_store'].invite('tester@example.test',admin['id'])
        tester=requests.Session();assert flow(tester,'tester@example.test',invite).status_code==200
        assert tester.get(base+'/api/private').status_code==403
        # A second browser can return after provider-managed recovery with the same subject.
        recovered=requests.Session();assert flow(recovered,'tester@example.test').status_code==200
        provider.config['CLAIM_OVERRIDES']={'nonce':'wrong'}
        denied=requests.Session();assert flow(denied).status_code==403
        assert denied.get(base+'/api/private').status_code==401
        provider.config['CLAIM_OVERRIDES']={'aud':'different-client'}
        assert flow(requests.Session()).status_code==403
        provider.config['CLAIM_OVERRIDES']={'iss':'https://wrong.invalid'}
        assert flow(requests.Session()).status_code==403
    finally:
        server.shutdown();provider_server.shutdown()


def test_favicon_and_second_signin_do_not_expire_visible_form(app, monkeypatch):
    import re
    from flask import redirect
    c=app.test_client();html=c.get('/auth/signin').text
    csrf=re.search(r'name="csrf" value="([^"]+)"',html)[1]
    assert c.get('/favicon.ico').status_code==204
    c.get('/auth/signin')
    monkeypatch.setattr(app.extensions['auth_oidc'],'authorize_redirect',lambda *a,**kw:redirect('https://idp.invalid/authorize'))
    assert c.post('/auth/start',data={'csrf':csrf}).status_code==302


def test_non_ascii_security_tokens_are_rejected(app):
    c=app.test_client()
    assert c.post('/auth/start',data={'csrf':'é'}).status_code==400
    assert c.get('/auth/callback?state=%C3%A9').status_code==400
    login(app,c)
    assert c.post('/api/private',data={'csrf':'é'}).status_code==403


def test_oidc_network_timeout_is_configured(app):
    with app.extensions['auth_oidc']._get_oauth_client() as client:
        assert client.default_timeout == 10
