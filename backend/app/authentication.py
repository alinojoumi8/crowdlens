"""OIDC invitation sign-in. Tester access stays closed until administrator-owned quotas exist."""
import secrets
from functools import wraps
from urllib.parse import urlparse
from flask import Blueprint, g, jsonify, redirect, render_template, request, session
from authlib.integrations.flask_client import OAuth
from .services.auth_store import AuthStore
from .services import workspace


def install_authentication(app):
    mode = app.config.get('AUTH_MODE', 'local')
    if mode not in {'local', 'oidc'}:
        raise RuntimeError('AUTH_MODE must be local or oidc')
    if mode == 'local':
        workspace.configure()
        @app.get('/auth/status')
        def local_auth_status():
            return jsonify(enabled=False)
        return
    required = ['SECRET_KEY', 'AUTH_BASE_URL', 'AUTH_ISSUER', 'AUTH_CLIENT_ID',
                'AUTH_CLIENT_SECRET', 'AUTH_ADMIN_EMAIL', 'AUTH_DB_PATH']
    if any(not app.config.get(key) for key in required) or len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('OIDC authentication requires complete configuration and a strong SECRET_KEY')
    allow_http = app.config.get('AUTH_ALLOW_HTTP_LOOPBACK', False)
    for key in ['AUTH_BASE_URL', 'AUTH_ISSUER']:
        parsed = urlparse(app.config[key])
        if (parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname
                or (parsed.scheme != 'https' and not (allow_http and parsed.scheme == 'http'
                    and parsed.hostname in {'localhost', '127.0.0.1', '::1'}))):
            raise RuntimeError(f'{key} must use HTTPS (explicit loopback HTTP is only for local tests)')
    if urlparse(app.config['AUTH_BASE_URL']).path not in {'', '/'}:
        raise RuntimeError('AUTH_BASE_URL must be an origin without a path')
    base = app.config['AUTH_BASE_URL'].rstrip('/')
    issuer = app.config['AUTH_ISSUER']
    secure = urlparse(base).scheme == 'https'
    app.config.update(SESSION_COOKIE_NAME='crowdlens_oidc', SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SECURE=secure, SESSION_COOKIE_SAMESITE='Lax')
    store = AuthStore(app.config['AUTH_DB_PATH'], issuer, app.config['AUTH_ADMIN_EMAIL'])
    workspace.configure(app.config['AUTH_DB_PATH'])
    app.extensions['auth_store'] = store
    oauth = OAuth(app)
    remote = oauth.register('identity', client_id=app.config['AUTH_CLIENT_ID'],
        client_secret=app.config['AUTH_CLIENT_SECRET'],
        server_metadata_url=issuer.rstrip('/')+'/.well-known/openid-configuration',
        client_kwargs={'scope':'openid email', 'code_challenge_method':'S256', 'default_timeout':10})
    app.extensions['auth_oidc'] = remote
    bp = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates')

    def same_token(expected, supplied):
        return bool(supplied) and secrets.compare_digest(expected.encode(), supplied.encode())

    def page(**kwargs):
        return render_template('authentication.html', user=getattr(g, 'auth_user', None), **kwargs)

    @app.before_request
    def authenticate():
        g.auth_user = store.session(request.cookies.get('crowdlens_auth', ''))
        g.workspace_token = workspace._SCOPE.set(g.auth_user['id'] if g.auth_user else None)
        public = {'auth.signin', 'auth.start', 'auth.callback', 'auth.status', 'auth.privacy'}
        if request.path == '/favicon.ico':
            return '', 204
        if request.endpoint in public or request.path == '/health':
            return None
        user = g.auth_user
        if not user:
            if request.path.startswith('/api/'):
                return jsonify(success=False, error='authentication_required'), 401
            return redirect('/auth/signin')
        if request.endpoint not in {'auth.account', 'auth.logout', 'auth.revoke_sessions'} and user['role'] != 'admin':
            return jsonify(success=False, error='workspace_access_not_enabled'), 403
        if request.path.startswith('/api/'):
            workspace.check_request_references(request)
        if request.method not in {'GET','HEAD','OPTIONS'}:
            if request.headers.get('Origin') and request.headers['Origin'] != base:
                return jsonify(success=False, error='origin_not_allowed'), 403
            supplied = request.headers.get('X-CrowdLens-CSRF') or request.form.get('csrf', '')
            if not same_token(user['csrf'], supplied):
                return jsonify(success=False, error='csrf_required'), 403

    # Like WorkflowHalt, permission denial bypasses broad service fallback
    # handlers. Catch it around preprocessing, views and response publication.
    dispatch = app.full_dispatch_request
    @wraps(dispatch)
    def workspace_dispatch():
        try:
            return dispatch()
        except workspace.WorkspaceDenied:
            return app.finalize_request((jsonify(success=False, error='resource_not_found'), 404))
    app.full_dispatch_request = workspace_dispatch

    @app.teardown_request
    def clear_workspace(exc):
        token = g.pop('workspace_token', None)
        if token is not None:
            workspace._SCOPE.reset(token)

    @app.after_request
    def authentication_headers(response):
        if getattr(g, 'auth_user', None) and request.path.startswith('/api/'):
            workspace._store.audit(g.auth_user['id'], request.method + ':' + str(response.status_code), request.endpoint or '')
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'strict-origin'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @bp.get('/status')
    def status():
        return jsonify(enabled=True, authenticated=bool(g.auth_user))

    @bp.get('/signin')
    def signin():
        session.setdefault('form_csrf', secrets.token_urlsafe(32))
        return page(screen='signin', csrf=session['form_csrf'])

    @bp.post('/start')
    def start():
        if not same_token(session.pop('form_csrf', ''), request.form.get('csrf', '')):
            return page(screen='error', error='Sign-in form expired. Please start again.'), 400
        invitation = request.form.get('invitation', '').strip()
        if len(invitation) > 128:
            return page(screen='error', error='Invalid invitation.'), 400
        # State-bound invitation, never a URL parameter or logged provider payload.
        state = secrets.token_urlsafe(32)
        session['invitation'] = invitation
        session['login_state'] = state
        try:
            return remote.authorize_redirect(base+'/auth/callback', state=state,
                                             nonce=secrets.token_urlsafe(32), prompt='login')
        except Exception:
            session.clear()
            return page(screen='error', error='The identity provider is unavailable. Please try again later.'), 503

    @bp.get('/callback')
    def callback():
        if not same_token(session.pop('login_state', ''), request.args.get('state', '')):
            session.clear()
            return page(screen='error', error='Sign-in could not be verified. Please start again.'), 400
        invitation = session.pop('invitation', '')
        try:
            token = remote.authorize_access_token()
            claims = token.get('userinfo')
            if not token.get('id_token') or not claims:
                raise ValueError('A verified OpenID identity is required.')
            user = store.admit(claims, invitation)
        except Exception:
            session.clear()
            return page(screen='error', error='Sign-in denied. Check your invitation, verified email and MFA, or contact the operator.'), 403
        store.revoke(request.cookies.get('crowdlens_auth', ''))
        session.clear()
        auth_token, csrf = store.new_session(user['id'])
        response = redirect('/auth/account')
        response.set_cookie('crowdlens_auth', auth_token, max_age=28800, secure=secure, httponly=True, samesite='Lax')
        response.set_cookie('crowdlens_csrf', csrf, max_age=28800, secure=secure, httponly=False, samesite='Lax')
        return response

    @bp.get('/account')
    def account():
        return page(screen='account', accounts=store.accounts() if g.auth_user['role']=='admin' else [])

    @bp.post('/invitations')
    def invitations():
        try:
            token = store.invite(request.form.get('email',''), g.auth_user['id'])
        except ValueError as exc:
            return page(screen='error', error=str(exc)), 400
        return page(screen='invitation', invitation=token)

    @bp.post('/accounts/<user_id>/suspend')
    def suspend(user_id):
        try:
            store.suspend(user_id, request.form.get('suspended')=='true', g.auth_user['id'])
        except ValueError as exc:
            return page(screen='error', error=str(exc)), 400
        return redirect('/auth/account')

    def logout_response():
        session.clear()
        response = redirect('/auth/signin')
        response.delete_cookie('crowdlens_auth', secure=secure, httponly=True, samesite='Lax')
        response.delete_cookie('crowdlens_csrf', secure=secure, samesite='Lax')
        return response

    @bp.post('/logout')
    def logout():
        store.revoke(request.cookies.get('crowdlens_auth',''))
        return logout_response()

    @bp.post('/revoke-sessions')
    def revoke_sessions():
        store.revoke_all(g.auth_user['id'])
        return logout_response()

    @bp.get('/privacy')
    def privacy():
        return page(screen='privacy')

    app.register_blueprint(bp)
