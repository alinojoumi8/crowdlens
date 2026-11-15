"""Consistent API error sanitization at the final HTTP boundary."""

from __future__ import annotations

import logging

from flask import jsonify, request

logger = logging.getLogger('mirofish.request')


def reject_malformed_json():
    """Answer 400, not 500, when a JSON body is malformed or is not an object."""
    if request.method not in ('POST', 'PUT', 'PATCH') or not request.is_json or not request.get_data(cache=True):
        return None
    if isinstance(request.get_json(silent=True), dict):
        return None
    return jsonify({
        "success": False, "error": "Request body must be a JSON object", "error_code": "invalid_json",
    }), 400


def sanitize_error_response(app, response, request_id: str):
    """Strip internal diagnostics from JSON 5xx responses by default."""
    if (
        response.status_code < 500
        or not response.is_json
        or app.config.get("EXPOSE_INTERNAL_ERRORS", False)
    ):
        return response

    payload = response.get_json(silent=True)
    if not isinstance(payload, dict):
        return response

    payload.pop("traceback", None)
    if app.config.get("AUTH_MODE", "local") == "oidc" and payload.get("error"):
        # Exception text can hold server paths and provider details; other users must not see it.
        logger.error("Internal error hidden from client: request_id=%s error=%s", request_id, payload["error"])
        payload["error"] = "Internal server error"
    payload.setdefault("success", False)
    payload.setdefault("error", "Internal server error")
    payload.setdefault("error_code", "internal_error")
    payload.setdefault("request_id", request_id)
    response.set_data(app.json.dumps(payload))
    response.content_type = "application/json"
    return response
