"""
Guard: CUE API keys are accepted ONLY by the endpoints on the explicit allow-list
(plan 11 B1.2). Any new endpoint that accepts an API key fails this test until the
allow-list (and the plan) are updated on purpose.
"""
from fastapi.routing import APIRoute

from core.security import APIKeyBearer, JWTOrAPIKeyBearer

EXPECTED = {
    # /v2/upload/* (Authorization: Bearer, file:upload)
    ("POST", "/v2/upload/prepare-single"),
    ("POST", "/v2/upload/complete-single"),
    ("POST", "/v2/upload/multipart/start"),
    ("POST", "/v2/upload/multipart/get-part-url"),
    ("POST", "/v2/upload/multipart/complete"),
    ("POST", "/v2/upload/multipart/abort"),
    # apiKey in the JSON body (file:read)
    ("POST", "/v2/files/list"),
    # JWT or API key (file:upload)
    ("GET", "/v2/me/upload-targets"),
}


def _calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _calls(dep)


def _body_has_api_key(route: APIRoute) -> bool:
    for param in route.dependant.body_params:
        annotation = getattr(param.field_info, "annotation", None) or getattr(param, "type_", None)
        fields = getattr(annotation, "model_fields", {}) or {}
        if "apiKey" in fields:
            return True
    return False


def _api_key_routes(app):
    found = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        accepts_key = any(isinstance(c, (APIKeyBearer, JWTOrAPIKeyBearer)) for c in _calls(route.dependant))
        if accepts_key or _body_has_api_key(route):
            for method in route.methods:
                found.add((method, route.path))
    return found


def test_api_key_allowlist(app):
    assert _api_key_routes(app) == EXPECTED
