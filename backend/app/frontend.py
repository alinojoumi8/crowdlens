"""Serve a built SPA without masking missing API endpoints or assets."""
from pathlib import Path
import re

from flask import abort, send_from_directory


def install_frontend(app, directory):
    root = Path(directory).resolve()
    if not (root / 'index.html').is_file():
        raise RuntimeError('FRONTEND_DIST_DIR must contain a built index.html; run npm run build.')

    @app.get('/')
    @app.get('/<path:path>')
    def frontend(path=''):
        parts = path.split('/')
        if parts[0] in {'api', 'health'} or '\\' in path or any(p.startswith('.') for p in parts):
            abort(404)
        target = (root / path).resolve()
        if not target.is_relative_to(root):
            abort(404)
        if target.is_file():
            immutable = path.startswith('assets/') and re.search(r'-[A-Za-z0-9_-]{8,}\.', path)
            response = send_from_directory(root, path, max_age=31536000 if immutable else 0)
            if immutable:
                response.cache_control.immutable = True
            else:
                response.headers['Cache-Control'] = 'no-cache'
            return response
        if parts[0] == 'assets' or Path(path).suffix:
            abort(404)
        response = send_from_directory(root, 'index.html', max_age=0)
        response.headers['Cache-Control'] = 'no-cache'
        return response
