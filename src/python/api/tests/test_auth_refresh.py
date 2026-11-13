"""POST /v2/auth/refresh: 401 only for a bad refresh token, 502 when IDFS is blocked or down.

Clients sign the user out on 401 and keep the session on 502, so an IDFS outage
(e.g. the Nov 2026 VPN-only lockdown, where IDFS answered 403) doesn't sign everyone out.
Keycloak HTTP calls are mocked.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import build_app

ISSUER = "https://idfs.uat.earthdatacloud.nasa.gov/realms/cue"
TOKENS = {"access_token": "at", "refresh_token": "rt2", "expires_in": 300}


@pytest.fixture
def keycloak(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ISSUER", ISSUER)
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_ID", "cue-uat")
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "secret")

    class KC:
        handler = staticmethod(lambda req: httpx.Response(200, json=TOKENS))

    KC.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: KC.handler(req)))
    return KC


@pytest.fixture
def client(keycloak):
    app = build_app()
    app.state.http_client = keycloak.client
    return TestClient(app)


def refresh(client):
    return client.post("/v2/auth/refresh", json={"refresh_token": "rt"})


def test_refresh_ok(client):
    r = refresh(client)
    assert r.status_code == 200
    assert r.json()["access_token"] == "at"


@pytest.mark.parametrize("kc_status", [400, 401])
def test_bad_refresh_token_is_401(client, keycloak, kc_status):
    keycloak.handler = staticmethod(lambda req: httpx.Response(kc_status, json={"error": "invalid_grant"}))
    assert refresh(client).status_code == 401


@pytest.mark.parametrize("kc_status", [403, 500, 503])
def test_idfs_blocked_or_down_is_502(client, keycloak, kc_status):
    keycloak.handler = staticmethod(lambda req: httpx.Response(kc_status, text="Forbidden"))
    r = refresh(client)
    assert r.status_code == 502
    assert "Forbidden" not in r.text


def test_network_error_is_502(client, keycloak):
    def boom(req):
        raise httpx.ConnectError("no route", request=req)
    keycloak.handler = staticmethod(boom)
    assert refresh(client).status_code == 502
