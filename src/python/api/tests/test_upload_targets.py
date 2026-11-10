"""GET /v2/me/upload-targets (plan 11 B1, plan 17 section 3)."""
import uuid

import pytest

from conftest import NGROUP_A, NGROUP_B, key_row, user_record
from v2.database_util import upload_targets as targets_db

C1, C2, C3 = (uuid.UUID(int=i) for i in (101, 102, 103))
P1, P2, P3 = (uuid.UUID(int=i) for i in (201, 202, 203))


def row(cid, cname, pid, pname, active=True, can_upload=True, primary=None, ngroup=NGROUP_A):
    return {
        "collection_id": cid, "collection_short_name": cname, "active": active,
        "primary_provider_id": primary or pid,
        "ngroup_id": ngroup, "ngroup_short_name": "GHRC",
        "provider_id": pid, "provider_short_name": pname, "provider_long_name": pname + " long",
        "can_upload": can_upload,
    }


ROWS = [
    row(C1, "goesr_glm_l2", P1, "GLMTEAM"),
    row(C1, "goesr_glm_l2", P2, "OTHER", can_upload=False, primary=P1),
    row(C2, "inactive_coll", P1, "GLMTEAM", active=False),
    row(C3, "blocked_coll", P3, "BLOCKED", can_upload=False),
]


@pytest.fixture
def fake_db(monkeypatch):
    calls = {}

    async def all_rows(conn):
        calls["scope"] = "all"
        return ROWS

    async def ngroup_rows(conn, ngroup_ids):
        calls["scope"] = "ngroups"
        calls["ngroups"] = ngroup_ids
        return ROWS

    async def assigned_rows(conn, user_id, ngroup_ids):
        calls["scope"] = "assigned"
        calls["user_id"] = user_id
        calls["ngroups"] = ngroup_ids
        return calls.get("assigned_rows", ROWS)

    async def user_name(conn, user_id):
        return "Jane From DB"

    monkeypatch.setattr(targets_db, "list_all_target_rows", all_rows)
    monkeypatch.setattr(targets_db, "list_ngroup_target_rows", ngroup_rows)
    monkeypatch.setattr(targets_db, "list_assigned_target_rows", assigned_rows)
    monkeypatch.setattr(targets_db, "get_user_name", user_name)

    async def ngroup(conn, ngroup_id):
        return {"id": ngroup_id, "short_name": "GHRC" if ngroup_id == NGROUP_A else "ASDC"}

    monkeypatch.setattr(targets_db, "get_ngroup", ngroup)
    return calls


def test_admin_sees_all_uploadable(client, fake_db, as_jwt_user):
    headers = as_jwt_user(uuid.uuid4(), ["admin"], [])
    r = client.get("/v2/me/upload-targets", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert fake_db["scope"] == "all"
    assert body["auth_kind"] == "jwt"
    assert body["caller"] == {"auth_kind": "jwt", "name": "Jane From DB", "key": None}
    names = [t["collection_short_name"] for t in body["targets"]]
    assert names == ["goesr_glm_l2"]
    t = body["targets"][0]
    assert t["uploadable"] is True and t["reasons"] == []
    assert [p["short_name"] for p in t["providers"]] == ["GLMTEAM", "OTHER"]
    assert t["primary_provider_id"] == str(P1)
    assert t["ngroup"] == {"id": str(NGROUP_A), "short_name": "GHRC"}


def test_include_unavailable_returns_reasons(client, fake_db, as_jwt_user):
    headers = as_jwt_user(uuid.uuid4(), ["admin"], [])
    r = client.get("/v2/me/upload-targets?include_unavailable=true", headers=headers)
    by_name = {t["collection_short_name"]: t for t in r.json()["targets"]}
    assert set(by_name) == {"goesr_glm_l2", "inactive_coll", "blocked_coll"}
    assert by_name["inactive_coll"]["reasons"] == ["collection_inactive"]
    assert by_name["inactive_coll"]["uploadable"] is False
    assert by_name["blocked_coll"]["reasons"] == ["provider_uploads_disabled"]


def test_search_matches_collection_or_provider(client, fake_db, as_jwt_user):
    headers = as_jwt_user(uuid.uuid4(), ["admin"], [])
    r = client.get("/v2/me/upload-targets?include_unavailable=true&search=blocked", headers=headers)
    assert [t["collection_short_name"] for t in r.json()["targets"]] == ["blocked_coll"]
    r = client.get("/v2/me/upload-targets?include_unavailable=true&search=glmteam", headers=headers)
    assert {t["collection_short_name"] for t in r.json()["targets"]} == {"goesr_glm_l2", "inactive_coll"}


def test_search_too_long_rejected(client, fake_db, as_jwt_user):
    headers = as_jwt_user(uuid.uuid4(), ["admin"], [])
    r = client.get("/v2/me/upload-targets?search=" + "x" * 101, headers=headers)
    assert r.status_code == 422


@pytest.mark.parametrize("role", ["daac_manager", "daac_staff", "security"])
def test_daac_roles_use_ngroup_scope(client, fake_db, as_jwt_user, role):
    headers = as_jwt_user(uuid.uuid4(), [role], [NGROUP_A, NGROUP_B])
    r = client.get("/v2/me/upload-targets", headers=headers)
    assert r.status_code == 200
    assert fake_db["scope"] == "ngroups"
    assert set(fake_db["ngroups"]) == {NGROUP_A, NGROUP_B}


def test_data_provider_uses_assigned_scope(client, fake_db, as_jwt_user):
    uid = uuid.uuid4()
    headers = as_jwt_user(uid, ["provider"], [NGROUP_A])
    r = client.get("/v2/me/upload-targets", headers=headers)
    assert r.status_code == 200
    assert fake_db["scope"] == "assigned"
    assert fake_db["user_id"] == uid
    assert fake_db["ngroups"] == [NGROUP_A]


def test_data_provider_without_assignments_gets_empty_list(client, fake_db, as_jwt_user):
    fake_db["assigned_rows"] = []
    headers = as_jwt_user(uuid.uuid4(), ["provider"], [NGROUP_A])
    r = client.get("/v2/me/upload-targets", headers=headers)
    assert r.status_code == 200
    assert r.json()["targets"] == []


def test_personal_key_same_result_as_jwt_and_caller_key_info(client, fake_db, as_jwt_user, as_api_key):
    uid = uuid.uuid4()
    jwt_headers = as_jwt_user(uid, ["provider"], [NGROUP_A])
    jwt_targets = client.get("/v2/me/upload-targets", headers=jwt_headers).json()["targets"]

    k = key_row(user_id=uid, scopes=["file:upload", "file:read"])
    key_headers = as_api_key(k, user_record(uid, ["provider"], [NGROUP_A]))
    r = client.get("/v2/me/upload-targets", headers=key_headers)
    assert r.status_code == 200
    body = r.json()
    assert fake_db["scope"] == "assigned" and fake_db["user_id"] == uid
    assert body["targets"] == jwt_targets
    assert body["auth_kind"] == "api_key"
    caller = body["caller"]
    assert caller["auth_kind"] == "api_key"
    assert caller["name"] == "Jane Doe"
    assert caller["key"]["name"] == "CUE Desktop - LAPTOP-7"
    assert caller["key"]["suffix"] == "x7Qa"
    assert caller["key"]["scopes"] == ["file:upload", "file:read"]
    assert caller["key"]["type"] == "personal"
    assert caller["key"]["expires_at"]
    # Never any secret material in the response.
    assert "cue_sk_" not in r.text and "key_hash" not in r.text


def test_proxy_key_uses_key_ngroup_and_key_name(client, fake_db, as_api_key):
    k = key_row(user_id=None, key_type="proxy", proxy_user_name="GHRC Ingest Bot",
                ngroup_id=NGROUP_B, name="GHRC ingest proxy")
    r = client.get("/v2/me/upload-targets", headers=as_api_key(k))
    assert r.status_code == 200
    assert fake_db["scope"] == "ngroups"
    assert fake_db["ngroups"] == [NGROUP_B]
    caller = r.json()["caller"]
    assert caller["name"] == "GHRC ingest proxy"
    assert caller["key"]["type"] == "proxy"


def test_key_without_upload_scope_is_403(client, fake_db, as_api_key):
    uid = uuid.uuid4()
    k = key_row(user_id=uid, scopes=["file:read"])
    r = client.get("/v2/me/upload-targets", headers=as_api_key(k, user_record(uid, ["provider"], [NGROUP_A])))
    assert r.status_code == 403


def test_invalid_key_is_401(client, fake_db, as_api_key):
    r = client.get("/v2/me/upload-targets", headers=as_api_key(None))
    assert r.status_code == 401


def test_missing_auth_rejected(client, fake_db):
    r = client.get("/v2/me/upload-targets")
    assert r.status_code in (401, 403)
