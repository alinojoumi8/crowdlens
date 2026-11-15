"""API boundary defects from the 2026-11-14 review: body shape, error text, overlap."""
import pytest
from flask import Flask, jsonify, request

from app.services.graph_builder import GraphBuilderService
from app.utils.error_handling import reject_malformed_json, sanitize_error_response


def make_app(**config):
    app = Flask(__name__)
    app.config.update(config)
    app.before_request(reject_malformed_json)
    app.after_request(lambda response: sanitize_error_response(app, response, 'req-1'))

    @app.route('/echo', methods=['POST'])
    def echo():
        return jsonify(success=True, data=(request.get_json(silent=True) or {}).get('value'))

    @app.route('/boom', methods=['GET'])
    def boom():
        return jsonify(success=False, error="[Errno 13] Permission denied: '/app/backend/uploads/x.db'"), 500

    return app.test_client()


@pytest.mark.parametrize('body', ['{not json', '[1, 2]', '"text"', '7', 'null'])
def test_json_body_must_be_an_object(body):
    response = make_app().post('/echo', data=body, content_type='application/json')

    assert response.status_code == 400
    assert response.get_json() == {
        'success': False, 'error': 'Request body must be a JSON object', 'error_code': 'invalid_json'}


def test_object_bodies_empty_bodies_and_form_bodies_still_pass():
    client = make_app()

    assert client.post('/echo', json={'value': 3}).get_json() == {'success': True, 'data': 3}
    assert client.post('/echo', data='', content_type='application/json').status_code == 200
    assert client.post('/echo', data={'value': '3'}).status_code == 200


def test_managed_mode_hides_internal_error_text():
    payload = make_app(AUTH_MODE='oidc').get('/boom').get_json()

    assert payload['error'] == 'Internal server error'
    assert payload['request_id'] == 'req-1'
    assert 'uploads' not in str(payload)


def test_local_operator_still_sees_the_error_text():
    assert 'Permission denied' in make_app(AUTH_MODE='local').get('/boom').get_json()['error']


@pytest.mark.parametrize('size,requested,expected', [(500, 499, 250), (500, 200, 200), (1000, 5000, 500), (3000, 200, 200)])
def test_overlap_is_limited_to_half_the_chunk_size(size, requested, expected):
    settings = GraphBuilderService.resolve_build_settings({'chunk_size': size, 'chunk_overlap': requested})

    assert settings['chunk_overlap'] == expected
