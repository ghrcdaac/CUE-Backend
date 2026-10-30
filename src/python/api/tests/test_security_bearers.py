"""
Regression tests: the existing APIKeyBearer and OIDCBearer behave as before after
the shared-helper refactor, and POST /v2/files/list (apiKey in the body) still works.
"""
import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from conftest import NGROUP_A, FakePool, key_row, user_record
from core.security import APIKeyBearer, OIDCBearer


def _app_with(dep):
    app = FastAPI()
    app.state.pool = FakePool()
    app.state.jwks_keys = {"keys": []}

    @app.middleware("http")
    async def attach_pool(request, call_next):
        request.state.pool = app.state.pool
        return await call_next(request)

    @app.get("/who")
    async def who(user=Depends(dep)):
        return {"id": str(user.id), "roles": user.roles, "ngroups": user.ngroups, "name": user.name}

    return TestClient(app)


def test_api_key_bearer_personal_key(as_api_key):
    uid = uuid.uuid4()
    headers = as_api_key(key_row(user_id=uid), user_record(uid, ["provider"], [NGROUP_A]))
    r = _app_with(APIKeyBearer(required_scopes=["file:upload"])).get("/who", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"id": str(uid), "roles": ["provider"], "ngroups": [str(NGROUP_A)], "name": "Jane Doe"}


def test_api_key_bearer_proxy_key(as_api_key):
    creator = uuid.uuid4()
    k = key_row(user_id=None, key_type="proxy", proxy_user_name="Ingest Bot", created_by=creator)
    r = _app_with(APIKeyBearer(required_scopes=["file:upload"])).get("/who", headers=as_api_key(k))
    assert r.status_code == 200
    assert r.json() == {"id": str(creator), "roles": ["proxy"], "ngroups": [str(NGROUP_A)], "name": "Ingest Bot"}


def test_api_key_bearer_errors(as_api_key):
    client = _app_with(APIKeyBearer(required_scopes=["file:upload"]))
    assert client.get("/who", headers=as_api_key(None)).status_code == 401
    uid = uuid.uuid4()
    no_scope = as_api_key(key_row(user_id=uid, scopes=["file:read"]), user_record(uid, [], [NGROUP_A]))
    assert client.get("/who", headers=no_scope).status_code == 403
    missing_user = as_api_key(key_row(user_id=uid), None)
    assert client.get("/who", headers=missing_user).status_code == 401
    bad_proxy = as_api_key(key_row(user_id=None, key_type="proxy", proxy_user_name=None))
    assert client.get("/who", headers=bad_proxy).status_code == 401


def test_oidc_bearer_loads_db_roles(as_jwt_user):
    uid = uuid.uuid4()
    headers = as_jwt_user(uid, ["daac_staff"], [NGROUP_A])
    r = _app_with(OIDCBearer()).get("/who", headers=headers)
    assert r.status_code == 200
    assert r.json()["roles"] == ["daac_staff"]
    assert r.json()["ngroups"] == [str(NGROUP_A)]


def test_oidc_bearer_unregistered_user(monkeypatch, as_jwt_user):
    from core import security
    headers = as_jwt_user(uuid.uuid4(), [], [])

    async def none(conn, uid):
        return None

    monkeypatch.setattr(security.user_db, "get_user_auth_details", none)
    assert _app_with(OIDCBearer()).get("/who", headers=headers).status_code == 403


def test_oidc_bearer_active_ngroup_header(as_jwt_user):
    headers = as_jwt_user(uuid.uuid4(), ["provider"], [NGROUP_A])
    client = _app_with(OIDCBearer())
    assert client.get("/who", headers={**headers, "X-Active-Ngroup-Id": str(NGROUP_A)}).status_code == 200
    assert client.get("/who", headers={**headers, "X-Active-Ngroup-Id": str(uuid.uuid4())}).status_code == 403


def test_oidc_bearer_rejects_api_key_as_jwt():
    # Real validation (empty JWKS): a cue_sk_ key is not a JWT and must be rejected by OIDCBearer.
    r = _app_with(OIDCBearer()).get("/who", headers={"Authorization": "Bearer cue_sk_whatever"})
    assert r.status_code == 401


# --- POST /v2/files/list (apiKey in the JSON body) ---

@pytest.fixture
def files_db(monkeypatch):
    from v2.utils import file as file_utils
    seen = {}

    async def count(conn, **kw):
        seen["count_ngroup"] = kw["active_ngroup_id"]
        return 0

    async def listing(conn, **kw):
        seen["list_ngroup"] = kw["active_ngroup_id"]
        return []

    monkeypatch.setattr(file_utils.file_db, "count_files_for_ngroup", count)
    monkeypatch.setattr(file_utils.file_db, "list_files_paginated", listing)
    return seen


def _patch_key(monkeypatch, row):
    from v2.utils import file as file_utils

    async def fake_key(conn, key_hash):
        return row

    monkeypatch.setattr(file_utils.api_key_db, "get_user_from_api_key", fake_key)


def test_files_list_with_read_scope(client, monkeypatch, files_db):
    _patch_key(monkeypatch, key_row(user_id=uuid.uuid4(), scopes=["file:upload", "file:read"]))
    r = client.post("/v2/files/list", json={"apiKey": "cue_sk_abc"})
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert files_db["list_ngroup"] == NGROUP_A and files_db["count_ngroup"] == NGROUP_A


def test_files_list_without_read_scope_is_403(client, monkeypatch, files_db):
    _patch_key(monkeypatch, key_row(user_id=uuid.uuid4(), scopes=["file:upload"]))
    r = client.post("/v2/files/list", json={"apiKey": "cue_sk_abc"})
    assert r.status_code == 403
