"""Browser boundaries for local and authenticated pilot responses."""
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; "
       "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")


def install_response_security(app):
    @app.after_request
    def secure_response(response):
        response.headers['Content-Security-Policy'] = CSP
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if app.config.get('AUTH_MODE') == 'oidc' and app.config.get('AUTH_BASE_URL', '').startswith('https://'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        if 'attachment' in response.headers.get('Content-Disposition', '').lower():
            # Generated Markdown/JSON/scripts are data. Never let downloaded
            # source/model HTML acquire the application's browser origin.
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'"
            response.headers['Cache-Control'] = 'no-store'
        return response
