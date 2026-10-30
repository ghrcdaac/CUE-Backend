"""
Many-to-many mappings + audit history + strict upload rule (plan 11 B3) against a REAL
PostgreSQL database that already has the [GUI-1..7] objects.

Skipped unless CUE_GUI_TEST_PG_DSN is set. Point it at a LOCAL throwaway database only, e.g.
    docker run -d --rm --name cue-gui-sqltest -e POSTGRES_PASSWORD=test -p 55432:5432 postgres
    psql ... -f src/postgres/2-tables.sql            (fresh schema, includes the GUI objects)
    CUE_GUI_TEST_PG_DSN=postgresql://postgres:test@127.0.0.1:55432/postgres pytest -o addopts="" src/python/api/tests
The tests only insert rows with random ids/names and delete them afterwards.
"""
import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from conftest import build_app

DSN = os.getenv("CUE_GUI_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CUE_GUI_TEST_PG_DSN not set (needs a local test database)")


def _ids():
    return SimpleNamespace(**{k: uuid.uuid4() for k in (
        "ga", "gb", "admin", "dp", "mgr_b", "p1", "p2", "p3", "egress", "c1", "c2")}, tag=uuid.uuid4().hex[:8])


async def _seed(conn, i):
    t = i.tag
    await conn.execute("INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $3, $4), ($2, $5, $6)",
                       i.ga, i.gb, "GA_" + t, "Group A " + t, "GB_" + t, "Group B " + t)
    await conn.executemany("INSERT INTO cueuser (id, email, name, cueusername) VALUES ($1, $2, $3, $4)", [
        (i.admin, "admin@example.com", "Admin " + t, "admin_" + t), (i.dp, "dp@example.com", "Dana Provider", "dp_" + t),
        (i.mgr_b, "m@example.com", "Mgr B", "mgr_" + t)])
    await conn.executemany("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2)",
                           [(i.dp, i.ga), (i.mgr_b, i.gb)])
    await conn.executemany(
        "INSERT INTO provider (id, ngroup_id, short_name, long_name, can_upload, point_of_contact) "
        "VALUES ($1, $2, $3, $4, TRUE, $5)", [
            (i.p1, i.ga, "P1_" + t, "Provider 1 " + t, i.admin), (i.p2, i.ga, "P2_" + t, "Provider 2 " + t, i.admin),
            (i.p3, i.gb, "P3_" + t, "Provider 3 " + t, i.admin)])
    await conn.execute("INSERT INTO egress (id, type, path, config, ngroup_id) VALUES ($1, 's3', 'p', '{}', $2)",
                       i.egress, i.ga)
    await conn.executemany(
        "INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active) "
        "VALUES ($1, $2, $3, $4, $5, TRUE)", [(i.c1, i.ga, i.egress, "c1_" + t, i.p1), (i.c2, i.ga, i.egress, "c2_" + t, i.p2)])
    await conn.executemany("INSERT INTO collection_provider (collection_id, provider_id) VALUES ($1, $2)",
                           [(i.c1, i.p1), (i.c2, i.p2)])


async def _cleanup(conn, i):
    users, colls = [i.admin, i.dp, i.mgr_b], [i.c1, i.c2]
    await conn.execute("DELETE FROM mapping_history WHERE left_id = ANY($1::uuid[])", users + colls)
    await conn.execute("DELETE FROM collection_provider WHERE collection_id = ANY($1::uuid[])", colls)
    await conn.execute("DELETE FROM collection WHERE id = ANY($1::uuid[])", colls)
    await conn.execute("DELETE FROM egress WHERE id = $1", i.egress)
    await conn.execute("DELETE FROM cueuser_provider WHERE cueuser_id = ANY($1::uuid[])", users)
    await conn.execute("DELETE FROM cueuser_role WHERE cueuser_id = ANY($1::uuid[])", users)
    await conn.execute("DELETE FROM provider WHERE id = ANY($1::uuid[])", [i.p1, i.p2, i.p3])
    await conn.execute("DELETE FROM cueuser_ngroup WHERE cueuser_id = ANY($1::uuid[])", users)
    await conn.execute("DELETE FROM cueuser WHERE id = ANY($1::uuid[])", users)
    await conn.execute("DELETE FROM ngroup WHERE id = ANY($1::uuid[])", [i.ga, i.gb])

class LazyPool:
    """Creates the asyncpg pool inside the TestClient's event loop on first use."""

    def __init__(self):
        self.pool = None

    async def get(self):
        import asyncpg
        if self.pool is None:
            self.pool = await asyncpg.create_pool(DSN, min_size=1, max_size=4)
        return self.pool


@pytest.fixture
def env():
    ids = _ids()
    app = build_app()
    lazy = LazyPool()
    app.user_middleware.clear()
    app.middleware_stack = None

    @app.middleware("http")
    async def attach_real_pool(request, call_next):
        request.state.pool = await lazy.get()
        return await call_next(request)

    async def run(sql_fn):
        pool = await lazy.get()
        async with pool.acquire() as conn:
            return await sql_fn(conn)

    with TestClient(app) as client:
        client.run = lambda fn: client.portal.call(run, fn)

        async def seed(conn):
            await _seed(conn, ids)

        client.run(seed)
        try:
            yield SimpleNamespace(client=client, ids=ids, run=client.run, lazy=lazy)
        finally:
            async def cleanup(conn):
                await _cleanup(conn, ids)
            client.run(cleanup)
            if lazy.pool is not None:
                client.portal.call(lazy.pool.close)


def history(env, left_id):
    async def q(conn):
        return [(r["right_id"], r["action"]) for r in await conn.fetch(
            "SELECT right_id, action FROM mapping_history WHERE left_id = $1 ORDER BY occurred_at, action", left_id)]
    return env.run(q)


def test_collection_provider_crud_and_history(env, as_jwt_user):
    c, ids = env.client, env.ids
    h = as_jwt_user(ids.admin, ["admin"], [])
    base = f"/v2/collections/{ids.c1}/providers"

    r = c.get(base, headers=h)
    assert r.status_code == 200
    assert [(p["provider_id"], p["is_primary"]) for p in r.json()] == [(str(ids.p1), True)]

    r = c.post(base, json={"provider_id": str(ids.p2)}, headers=h)
    assert r.status_code == 201
    assert {p["provider_id"] for p in r.json()} == {str(ids.p1), str(ids.p2)}
    assert c.post(base, json={"provider_id": str(ids.p2)}, headers=h).status_code == 409
    r = c.post(base, json={"provider_id": str(ids.p3)}, headers=h)
    assert r.status_code == 400 and "same DAAC" in r.json()["detail"]
    assert c.post(base, json={"provider_id": str(uuid.uuid4())}, headers=h).status_code == 404
    assert c.post(base, json={"provider_id": str(ids.p2), "x": 1}, headers=h).status_code == 422

    # primary switch keeps the old primary mapped
    r = c.put(f"{base}/{ids.p2}/primary", headers=h)
    assert r.status_code == 200
    assert {(p["provider_id"], p["is_primary"]) for p in r.json()} == {(str(ids.p1), False), (str(ids.p2), True)}
    assert c.put(f"{base}/{ids.p3}/primary", headers=h).status_code == 400  # not mapped

    assert c.delete(f"{base}/{ids.p2}", headers=h).status_code == 400  # primary
    assert c.delete(f"{base}/{ids.p1}", headers=h).status_code == 204
    assert c.delete(f"{base}/{ids.p1}", headers=h).status_code == 404

    r = c.put(base, json={"provider_ids": [str(ids.p2), str(ids.p1)]}, headers=h)
    assert r.status_code == 200 and len(r.json()) == 2
    assert c.put(base, json={"provider_ids": [str(ids.p1)]}, headers=h).status_code == 400  # missing primary
    assert c.put(base, json={"provider_ids": [str(ids.p2), str(ids.p3)]}, headers=h).status_code == 400  # cross-DAAC

    actions = history(env, ids.c1)
    assert (ids.p2, "added") in actions
    assert (ids.p2, "primary_set") in actions and (ids.p1, "primary_unset") in actions
    assert actions.count((ids.p1, "removed")) == 1 and actions.count((ids.p1, "added")) == 1

    r = c.get(f"/v2/providers/{ids.p2}/collections", headers=h)
    assert r.status_code == 200
    assert {(x["collection_id"], x["is_primary"]) for x in r.json()} == {(str(ids.c1), True), (str(ids.c2), True)}

    # GET/list responses carry the optional providers field
    r = c.get(f"/v2/collections/{ids.c1}", headers=h)
    assert r.status_code == 200 and len(r.json()["providers"]) == 2
    h2 = as_jwt_user(ids.admin, ["admin"], [ids.ga])
    r = c.get("/v2/collections/", headers={**h2, "X-Active-Ngroup-Id": str(ids.ga)})
    assert r.status_code == 200
    by_name = {x["short_name"]: x for x in r.json()["collections"]}
    assert {p["short_name"] for p in by_name[f"c1_{ids.tag}"]["providers"]} == {f"P1_{ids.tag}", f"P2_{ids.tag}"}
    assert by_name[f"c1_{ids.tag}"]["provider"]["id"] == str(ids.p2)  # existing field unchanged


def test_non_admin_outside_daac_forbidden(env, as_jwt_user):
    c, ids = env.client, env.ids
    h = as_jwt_user(ids.mgr_b, ["daac_manager"], [ids.gb],
                    privileges=["collection:read", "collection:update", "user:read", "user:update", "provider:read"])
    assert c.get(f"/v2/collections/{ids.c1}/providers", headers=h).status_code == 403
    assert c.post(f"/v2/collections/{ids.c1}/providers", json={"provider_id": str(ids.p2)}, headers=h).status_code == 403
    assert c.get(f"/v2/cueusers/{ids.dp}/providers", headers=h).status_code == 403
    assert c.get(f"/v2/providers/{ids.p1}/collections", headers=h).status_code == 403
    no_priv = as_jwt_user(ids.dp, ["provider"], [ids.ga], privileges=[])
    assert c.get(f"/v2/collections/{ids.c1}/providers", headers=no_priv).status_code == 403


def test_user_provider_crud_and_history(env, as_jwt_user):
    c, ids = env.client, env.ids
    h = as_jwt_user(ids.admin, ["admin"], [])
    base = f"/v2/cueusers/{ids.dp}/providers"

    assert c.get(base, headers=h).json() == []
    r = c.post(base, json={"provider_id": str(ids.p1)}, headers=h)
    assert r.status_code == 201 and [p["provider_id"] for p in r.json()] == [str(ids.p1)]
    assert c.post(base, json={"provider_id": str(ids.p1)}, headers=h).status_code == 409
    assert c.post(base, json={"provider_id": str(ids.p3)}, headers=h).status_code == 400  # not in the user's DAACs
    assert c.post(f"/v2/cueusers/{uuid.uuid4()}/providers", json={"provider_id": str(ids.p1)}, headers=h).status_code == 404

    r = c.put(base, json={"provider_ids": [str(ids.p2)]}, headers=h)
    assert r.status_code == 200 and [p["provider_id"] for p in r.json()] == [str(ids.p2)]
    assert c.delete(f"{base}/{ids.p2}", headers=h).status_code == 204
    assert c.delete(f"{base}/{ids.p2}", headers=h).status_code == 404

    actions = history(env, ids.dp)
    assert len(actions) == 4
    assert set(actions) == {(ids.p1, "added"), (ids.p2, "added"), (ids.p1, "removed"), (ids.p2, "removed")}


def test_upload_targets_reflect_mapping_changes(env, as_jwt_user):
    c, ids = env.client, env.ids
    admin = as_jwt_user(ids.admin, ["admin"], [])
    c.post(f"/v2/cueusers/{ids.dp}/providers", json={"provider_id": str(ids.p2)}, headers=admin)

    dp = as_jwt_user(ids.dp, ["provider"], [ids.ga])
    names = {t["collection_short_name"] for t in c.get("/v2/me/upload-targets", headers=dp).json()["targets"]}
    assert names == {f"c2_{ids.tag}"}

    admin = as_jwt_user(ids.admin, ["admin"], [])
    c.post(f"/v2/collections/{ids.c1}/providers", json={"provider_id": str(ids.p2)}, headers=admin)
    dp = as_jwt_user(ids.dp, ["provider"], [ids.ga])
    names = {t["collection_short_name"] for t in c.get("/v2/me/upload-targets", headers=dp).json()["targets"]}
    assert names == {f"c1_{ids.tag}", f"c2_{ids.tag}"}


def test_legacy_patch_moves_primary_with_history(env, as_jwt_user):
    c, ids = env.client, env.ids
    h = as_jwt_user(ids.admin, ["admin"], [])
    r = c.patch(f"/v2/collections/{ids.c1}", json={"provider_id": str(ids.p2)}, headers=h)
    assert r.status_code == 200 and r.json()["provider_id"] == str(ids.p2)
    r = c.get(f"/v2/collections/{ids.c1}/providers", headers=h)
    assert [(p["provider_id"], p["is_primary"]) for p in r.json()] == [(str(ids.p2), True)]  # A removed (move)
    actions = set(history(env, ids.c1))
    assert {(ids.p2, "added"), (ids.p2, "primary_set"), (ids.p1, "primary_unset"), (ids.p1, "removed")} <= actions


def test_role_update_records_history(env, as_jwt_user):
    c, ids = env.client, env.ids
    h = as_jwt_user(ids.admin, ["admin"], [])
    c.post(f"/v2/cueusers/{ids.dp}/providers", json={"provider_id": str(ids.p1)}, headers=h)

    async def role_id(conn):
        rid = await conn.fetchval("SELECT id FROM role WHERE short_name = 'provider'")
        if rid is None:
            rid = await conn.fetchval(
                "INSERT INTO role (short_name, long_name) VALUES ('provider', 'Data Provider') RETURNING id")
        return rid
    rid = env.run(role_id)
    r = c.patch(f"/v2/cueusers/{ids.dp}/role", json={"role_id": str(rid), "provider_id": str(ids.p2)}, headers=h)
    assert r.status_code == 200, r.text
    actions = history(env, ids.dp)
    assert (ids.p1, "removed") in actions and (ids.p2, "added") in actions

    async def cleanup_role(conn):
        await conn.execute("DELETE FROM cueuser_role WHERE cueuser_id = $1", ids.dp)
    env.run(cleanup_role)


def test_provider_filters_identical_before_second_mapping(env):
    ids = env.ids

    async def q(conn):
        out = []
        for pid in (ids.p1, ids.p2, ids.p3):
            old = await conn.fetchval("SELECT count(*) FROM collection c WHERE c.provider_id = $1", pid)
            new = await conn.fetchval(
                "SELECT count(*) FROM collection c WHERE EXISTS (SELECT 1 FROM v_collection_provider vcp "
                "WHERE vcp.collection_id = c.id AND vcp.provider_id = $1)", pid)
            out.append((old, new))
        return out
    assert all(old == new for old, new in env.run(q))


def test_strict_and_legacy_upload_rule(env, monkeypatch):
    from structlog.testing import capture_logs
    from v2.type_util.auth import AuthUser
    from v2.utils import upload as upload_utils
    ids = env.ids
    c1 = f"c1_{ids.tag}"
    dp = AuthUser(id=ids.dp, roles=["provider"], ngroups=[str(ids.ga)])
    staff = AuthUser(id=ids.mgr_b, roles=["daac_staff"], ngroups=[str(ids.ga)])
    proxy = AuthUser(id=ids.admin, roles=["proxy"], ngroups=[str(ids.ga)])
    other_daac = AuthUser(id=ids.mgr_b, roles=["daac_staff"], ngroups=[str(ids.gb)])

    def run_check(user, mode):
        monkeypatch.setenv("UPLOAD_PROVIDER_CHECK_MODE", mode)

        async def fn(_conn):
            req = SimpleNamespace(state=SimpleNamespace(pool=await env.lazy.get()))
            return await upload_utils._validate_upload_permissions(req, c1, user)
        return env.run(fn)
    # legacy: Data Provider without assignment is allowed, but the would-deny log fires
    with capture_logs() as logs:
        assert run_check(dp, "legacy")["id"] == ids.c1
    assert any(e["event"] == "upload.permission_check.strict_would_deny" and e["reason"] == "not_assigned_to_provider"
               for e in logs)

    # strict: denied until assigned
    with pytest.raises(upload_utils.UploadValidationError, match="not assigned to a provider"):
        run_check(dp, "strict")
    assert run_check(staff, "strict")["id"] == ids.c1
    assert run_check(proxy, "strict")["id"] == ids.c1
    with pytest.raises(upload_utils.UploadValidationError, match="DAAC group"):
        run_check(other_daac, "strict")

    async def assign(conn):
        await conn.execute("INSERT INTO cueuser_provider VALUES ($1, $2)", ids.dp, ids.p1)
    env.run(assign)
    assert run_check(dp, "strict")["id"] == ids.c1
    with capture_logs() as logs:
        run_check(dp, "legacy")
    assert not any(e["event"] == "upload.permission_check.strict_would_deny" for e in logs)

    async def block(conn):
        await conn.execute("UPDATE provider SET can_upload = FALSE WHERE id = $1", ids.p1)
    env.run(block)
    with pytest.raises(upload_utils.UploadValidationError, match="none of the providers"):
        run_check(dp, "strict")
