"""Disposable loopback-only identity provider. NOT a deployable authentication service.

It deliberately lets tests choose an identity and mint signed fixture claims.
"""
import base64
import hashlib
import secrets
import threading
import time
from urllib.parse import urlencode
from flask import Flask, jsonify, redirect, render_template_string, request
from joserfc import jwt
from joserfc.jwk import RSAKey
from werkzeug.serving import make_server


def start_provider(trailing_slash=False):
    app=Flask('oidc-test-only')
    key=RSAKey.generate_key(2048, parameters={'kid':'fixture'})
    codes={}
    server=make_server('127.0.0.1',0,app,threaded=True)
    base=f'http://127.0.0.1:{server.server_port}'
    issuer=base+('/' if trailing_slash else '')
    @app.get('/.well-known/openid-configuration')
    def discovery():
        return jsonify(issuer=issuer,authorization_endpoint=base+'/authorize',token_endpoint=base+'/token',
            jwks_uri=base+'/jwks',response_types_supported=['code'],subject_types_supported=['public'],
            id_token_signing_alg_values_supported=['RS256'],token_endpoint_auth_methods_supported=['client_secret_basic'],
            code_challenge_methods_supported=['S256'])
    @app.get('/jwks')
    def jwks():return jsonify(keys=[key.as_dict(private=False)])
    @app.route('/authorize',methods=['GET','POST'])
    def authorize():
        if request.method=='GET':
            return render_template_string('''<h1>Local test identity provider</h1><p>Fixture only. No real passwords or accounts.</p>
                <form method="post">{% for k,v in args.items() %}<input type="hidden" name="{{k}}" value="{{v}}">{% endfor %}
                <label>Email <input name="email" value="admin@example.test"></label>
                <button>Sign in with test identity</button></form>''',args=request.args)
        args=request.form.to_dict()
        assert args['client_id']=='fixture-client' and args['code_challenge_method']=='S256'
        assert args['redirect_uri'].startswith('http://127.0.0.1:')
        code=secrets.token_urlsafe(24);codes[code]=args
        return redirect(args['redirect_uri']+'?'+urlencode({'code':code,'state':args['state']}))
    @app.post('/token')
    def token():
        auth=request.authorization
        if not auth or auth.username!='fixture-client' or auth.password!='fixture-secret':return jsonify(error='invalid_client'),401
        args=codes.pop(request.form.get('code'),None)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(request.form.get('code_verifier','').encode()).digest()).rstrip(b'=').decode()
        if not args or challenge!=args['code_challenge'] or request.form.get('redirect_uri')!=args['redirect_uri']:
            return jsonify(error='invalid_grant'),400
        now=int(time.time());email=args['email']
        claims={'iss':issuer,'sub':email,'aud':'fixture-client','iat':now,'exp':now+120,
                'nonce':args['nonce'],'email':email,'email_verified':True,'amr':['mfa']}
        claims.update(app.config.get('CLAIM_OVERRIDES',{}))
        return jsonify(access_token='unused-fixture-access-token',token_type='Bearer',expires_in=120,
                       id_token=jwt.encode({'alg':'RS256','kid':'fixture'},claims,key))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    return app,server,issuer
