"""New API key validation (plan 11 B4.1). The DB write is mocked."""
import uuid

import pytest

from conftest import NGROUP_A, NGROUP_B
from v2.utils import api_keys as api_key_utils

PRIVS = ["api-key:create", "file:upload", "file:read"]


@pytest.fixture
def stored(monkeypatch):
    calls = []

    async def fake_store(conn, *args):
        calls.append(args)
        return uuid.uuid4()

    monkeypatch.setattr(api_key_utils.api_key_db, "store_api_key", fake_store)
    return calls


def body(**over):
    b = {"name": "CUE Desktop - LAPTOP-7", "key_type": "personal", "scopes": ["file:upload", "file:read"],
         "expires_in_days": 90, "ngroup_id": str(NGROUP_A)}
    b.update(over)
    return b


def test_personal_key_with_upload_and_read(client, stored, as_jwt_user):
    h = as_jwt_user(uuid.uuid4(), ["provider"], [NGROUP_A], privileges=PRIVS)
    r = client.post("/v2/api-keys/", json=body(), headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["key"].startswith("cue_sk_")
    assert len(stored) == 1


def test_personal_key_foreign_ngroup_rejected(client, stored, as_jwt_user):
    h = as_jwt_user(uuid.uuid4(), ["provider"], [NGROUP_A], privileges=PRIVS)
    r = client.post("/v2/api-keys/", json=body(ngroup_id=str(NGROUP_B)), headers=h)
    assert r.status_code == 400 and "your own DAACs" in r.json()["detail"]
    assert stored == []


@pytest.mark.parametrize("scopes,fragment", [
    (["file:upload", "file:delete"], "Unsupported"),
    (["admin"], "Unsupported"),
])
def test_unsupported_scopes_rejected(client, stored, as_jwt_user, scopes, fragment):
    h = as_jwt_user(uuid.uuid4(), ["provider"], [NGROUP_A], privileges=PRIVS + ["file:delete"])
    r = client.post("/v2/api-keys/", json=body(scopes=scopes), headers=h)
    assert r.status_code == 400 and fragment in r.json()["detail"]
    assert stored == []


def test_scope_not_held_by_creator_rejected(client, stored, as_jwt_user):
    h = as_jwt_user(uuid.uuid4(), ["daac_observer"], [NGROUP_A], privileges=["api-key:create", "file:read"])
    r = client.post("/v2/api-keys/", json=body(scopes=["file:upload"]), headers=h)
    assert r.status_code == 400 and "don't have" in r.json()["detail"]
    r = client.post("/v2/api-keys/", json=body(scopes=["file:read"]), headers=h)
    assert r.status_code == 201


def test_manager_proxy_key_still_works(client, stored, as_jwt_user):
    h = as_jwt_user(uuid.uuid4(), ["daac_manager"], [NGROUP_A], privileges=PRIVS)
    r = client.post("/v2/api-keys/", json=body(key_type="proxy", proxy_user_name="Ingest Bot"), headers=h)
    assert r.status_code == 201, r.text


def test_manager_managed_key_still_works(client, stored, as_jwt_user, monkeypatch):
    async def allow(creator, key_info, conn):
        return True
    monkeypatch.setattr(api_key_utils, "_can_manager_access_key", allow)
    h = as_jwt_user(uuid.uuid4(), ["daac_manager"], [NGROUP_A], privileges=PRIVS)
    r = client.post("/v2/api-keys/", json=body(key_type="managed_user", target_user_id=str(uuid.uuid4())), headers=h)
    assert r.status_code == 201, r.text


def test_admin_exempt(client, stored, as_jwt_user):
    h = as_jwt_user(uuid.uuid4(), ["admin"], [], privileges=[])
    r = client.post("/v2/api-keys/", json=body(ngroup_id=str(NGROUP_B), scopes=["file:upload", "file:delete"]), headers=h)
    assert r.status_code == 201, r.text
