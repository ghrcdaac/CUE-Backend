"""Desktop sign-in endpoints /v2/auth/desktop/* (plan 11 B2). Keycloak HTTP calls are mocked."""
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import build_app

ISSUER = "https://idfs.uat.earthdatacloud.nasa.gov/realms/cue"
REDIRECT = "http://127.0.0.1:53117/callback"
VERIFIER = "a" * 64
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()
STATE = "s" * 32
TOKENS = {"access_token": "at", "id_token": "it", "refresh_token": "rt", "expires_in": 300, "refresh_expires_in": 1800}


@pytest.fixture
def kc_env(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ISSUER", ISSUER)
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_ID", "cue-uat")
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "secret")
    monkeypatch.setenv("DESKTOP_REDIRECT_URIS", f"{REDIRECT}, http://127.0.0.1:53118/callback")


@pytest.fixture
def keycloak():
    """A mock Keycloak. Set .handler to control responses; .requests records calls."""
    class KC:
        requests = []
        handler = staticmethod(lambda req: httpx.Response(200, json=TOKENS))

    def transport(request):
        KC.requests.append(request)
        return KC.handler(request)

    KC.requests = []
    KC.client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    return KC


@pytest.fixture
def dclient(kc_env, keycloak):
    app = build_app()
    app.state.http_client = keycloak.client
    return TestClient(app)


def login_body(**over):
    body = {"redirect_uri": REDIRECT, "code_challenge": CHALLENGE, "code_challenge_method": "S256", "state": STATE}
    body.update(over)
    return body


def token_body(**over):
    body = {"code": "abc.def", "redirect_uri": REDIRECT, "code_verifier": VERIFIER}
    body.update(over)
    return body


# --- disabled when DESKTOP_REDIRECT_URIS is empty ---

def test_routes_404_when_not_configured(monkeypatch, kc_env, keycloak):
    monkeypatch.setenv("DESKTOP_REDIRECT_URIS", "")
    app = build_app()
    app.state.http_client = keycloak.client
    c = TestClient(app)
    assert c.post("/v2/auth/desktop/login-url", json=login_body()).status_code == 404
    assert c.post("/v2/auth/desktop/token", json=token_body()).status_code == 404
    assert c.post("/v2/auth/desktop/logout", json={"refresh_token": "rt"}).status_code == 404
    assert c.post("/v2/auth/desktop/login-url", json={}).status_code == 404  # 404 before body validation
    assert keycloak.requests == []


def test_dashboard_login_url_unaffected(dclient):
    r = dclient.get("/v2/auth/login-url")
    assert r.status_code == 200
    q = parse_qs(urlparse(r.json()["login_url"]).query)
    assert q["scope"] == ["openid profile email offline_access"]
    assert "code_challenge" not in q


# --- login-url ---

def test_login_url_built_with_pkce(dclient):
    r = dclient.post("/v2/auth/desktop/login-url", json=login_body())
    assert r.status_code == 200
    url = urlparse(r.json()["login_url"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == f"{ISSUER}/protocol/openid-connect/auth"
    q = parse_qs(url.query)
    assert q["client_id"] == ["cue-uat"]
    assert q["response_type"] == ["code"]
    assert q["scope"] == ["openid profile email"]
    assert q["redirect_uri"] == [REDIRECT]
    assert q["state"] == [STATE]
    assert q["code_challenge"] == [CHALLENGE]
    assert q["code_challenge_method"] == ["S256"]
    assert "secret" not in r.text


def test_login_url_second_allowed_port(dclient):
    r = dclient.post("/v2/auth/desktop/login-url", json=login_body(redirect_uri="http://127.0.0.1:53118/callback"))
    assert r.status_code == 200


@pytest.mark.parametrize("redirect", [
    "http://127.0.0.1:53120/callback", "http://localhost:53117/callback",
    "http://127.0.0.1:53117/callback/", "http://evil.example.com/callback",
])
def test_login_url_redirect_not_allowed(dclient, redirect):
    assert dclient.post("/v2/auth/desktop/login-url", json=login_body(redirect_uri=redirect)).status_code == 400


@pytest.mark.parametrize("over", [
    {"code_challenge": "short"},
    {"code_challenge": CHALLENGE + "x"},
    {"code_challenge": CHALLENGE[:-1] + "="},
    {"code_challenge_method": "plain"},
    {"state": "tooshort"},
    {"state": "bad state with spaces!!"},
    {"extra": "field"},
])
def test_login_url_bad_input(dclient, over):
    assert dclient.post("/v2/auth/desktop/login-url", json=login_body(**over)).status_code == 422


# --- token ---

def test_token_exchange_sends_verifier_and_secret(dclient, keycloak):
    r = dclient.post("/v2/auth/desktop/token", json=token_body())
    assert r.status_code == 200
    assert r.json()["access_token"] == "at" and r.json()["refresh_token"] == "rt"
    req = keycloak.requests[-1]
    assert str(req.url) == f"{ISSUER}/protocol/openid-connect/token"
    form = parse_qs(req.content.decode())
    assert form["grant_type"] == ["authorization_code"]
    assert form["code"] == ["abc.def"]
    assert form["code_verifier"] == [VERIFIER]
    assert form["redirect_uri"] == [REDIRECT]
    assert form["client_id"] == ["cue-uat"]
    assert form["client_secret"] == ["secret"]


def test_token_redirect_not_allowed(dclient, keycloak):
    r = dclient.post("/v2/auth/desktop/token", json=token_body(redirect_uri="http://127.0.0.1:9999/callback"))
    assert r.status_code == 400
    assert keycloak.requests == []


@pytest.mark.parametrize("over", [
    {"code_verifier": "a" * 42},
    {"code_verifier": "a" * 129},
    {"code_verifier": "a" * 42 + "!"},
    {"code": ""},
    {"code": "c" * 2049},
    {"state": STATE},
])
def test_token_bad_input(dclient, over):
    assert dclient.post("/v2/auth/desktop/token", json=token_body(**over)).status_code == 422


@pytest.mark.parametrize("kc_status", [400, 401])
def test_token_wrong_verifier_or_code(dclient, keycloak, kc_status):
    keycloak.handler = staticmethod(lambda req: httpx.Response(kc_status, json={"error": "invalid_grant",
                                                                                "error_description": "PKCE verification failed"}))
    r = dclient.post("/v2/auth/desktop/token", json=token_body())
    assert r.status_code == 400
    assert r.json()["detail"] == "Sign-in could not be completed. Please try again."
    assert "PKCE" not in r.text and "invalid_grant" not in r.text


def test_token_keycloak_server_error_is_502(dclient, keycloak):
    keycloak.handler = staticmethod(lambda req: httpx.Response(503, text="down"))
    assert dclient.post("/v2/auth/desktop/token", json=token_body()).status_code == 502


def test_token_network_error_is_502(dclient, keycloak):
    def boom(req):
        raise httpx.ConnectError("no route", request=req)
    keycloak.handler = staticmethod(boom)
    assert dclient.post("/v2/auth/desktop/token", json=token_body()).status_code == 502


# --- logout ---

def test_logout_revokes_with_revoke_endpoint(dclient, keycloak):
    keycloak.handler = staticmethod(lambda req: httpx.Response(200))
    r = dclient.post("/v2/auth/desktop/logout", json={"refresh_token": "rt"})
    assert r.status_code == 204
    req = keycloak.requests[-1]
    assert str(req.url) == f"{ISSUER}/protocol/openid-connect/revoke"
    form = parse_qs(req.content.decode())
    assert form["token"] == ["rt"]
    assert form["token_type_hint"] == ["refresh_token"]
    assert form["client_secret"] == ["secret"]


@pytest.mark.parametrize("handler", [
    lambda req: httpx.Response(400, json={"error": "invalid_token"}),
    lambda req: httpx.Response(500),
])
def test_logout_always_204(dclient, keycloak, handler):
    keycloak.handler = staticmethod(handler)
    assert dclient.post("/v2/auth/desktop/logout", json={"refresh_token": "rt"}).status_code == 204


def test_logout_network_error_still_204(dclient, keycloak):
    def boom(req):
        raise httpx.ConnectError("no route", request=req)
    keycloak.handler = staticmethod(boom)
    assert dclient.post("/v2/auth/desktop/logout", json={"refresh_token": "rt"}).status_code == 204


def test_secrets_never_logged(dclient, keycloak):
    from structlog.testing import capture_logs
    with capture_logs() as logs:
        dclient.post("/v2/auth/desktop/login-url", json=login_body())
        dclient.post("/v2/auth/desktop/token", json=token_body())
        dclient.post("/v2/auth/desktop/logout", json={"refresh_token": "rt-secret-value"})
    dumped = repr(logs)
    for secret in (VERIFIER, CHALLENGE, STATE, "abc.def", "rt-secret-value", "'secret'"):
        assert secret not in dumped
    events = [e["event"] for e in logs]
    assert "desktop_auth.login_url.issued" in events
    assert "desktop_auth.token.exchanged" in events
    assert "desktop_auth.logout.revoked" in events


def test_logout_bad_body(dclient):
    assert dclient.post("/v2/auth/desktop/logout", json={"refresh_token": ""}).status_code == 422
    assert dclient.post("/v2/auth/desktop/logout", json={"refresh_token": "rt", "x": 1}).status_code == 422
