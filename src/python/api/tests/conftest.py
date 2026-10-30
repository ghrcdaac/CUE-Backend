"""
Shared fixtures for the API tests (desktop GUI support).

These tests run without a database: they build a FastAPI app from the v2 router
(without main.py's startup hooks) and attach a fake asyncpg pool. DB functions
are monkeypatched per test.

Run:  pytest -o addopts="" src/python/api/tests
"""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

os.environ.setdefault("XRAY_LOCAL_FLAG_NAME", "1")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    """Minimal asyncpg connection stand-in. Tests patch the DB util functions instead."""

    def transaction(self):
        return FakeTransaction()


class FakePool:
    def __init__(self):
        self.conn = FakeConn()

    def acquire(self):
        return self

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


def build_app() -> FastAPI:
    from v2.api import router

    app = FastAPI()
    app.state.pool = FakePool()
    app.state.jwks_keys = {"keys": []}

    @app.middleware("http")
    async def attach_pool(request, call_next):
        request.state.pool = app.state.pool
        return await call_next(request)

    app.include_router(router, prefix="/v2")
    return app


@pytest.fixture
def app():
    return build_app()


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Identity helpers
# ---------------------------------------------------------------------------
NGROUP_A = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
NGROUP_B = uuid.UUID("00000000-0000-0000-0000-0000000000a2")


def user_record(user_id, roles, ngroups, name="Jane Doe", privileges=None, providers=None):
    """Shape returned by v2.database_util.cueuser.get_user_by_id (JSON columns as strings)."""
    return {
        "id": user_id,
        "email": "jane@example.com",
        "name": name,
        "cueusername": "jane",
        "edpub_id": None,
        "registered": datetime.now(timezone.utc),
        "roles": json.dumps(roles),
        "ngroups": json.dumps([{"id": str(n), "short_name": f"G{i}"} for i, n in enumerate(ngroups)]),
        "providers": json.dumps(providers or []),
        "privileges": json.dumps(privileges or []),
    }


def auth_details(roles, ngroups, privileges=None):
    """Shape returned by v2.database_util.cueuser.get_user_auth_details."""
    return {
        "roles": json.dumps(roles),
        "ngroups": json.dumps([{"id": str(n), "short_name": "G"} for n in ngroups]),
        "privileges": json.dumps(privileges or []),
    }


def key_row(user_id=None, scopes=("file:upload",), key_type="personal", ngroup_id=NGROUP_A,
            proxy_user_name=None, created_by=None, name="CUE Desktop - LAPTOP-7"):
    """Shape returned by v2.database_util.api_keys.get_user_from_api_key."""
    return {
        "user_id": user_id,
        "proxy_user_name": proxy_user_name,
        "ngroup_id": ngroup_id,
        "scopes": list(scopes),
        "created_by_user_id": created_by or user_id or uuid.uuid4(),
        "id": uuid.uuid4(),
        "name": name,
        "key_type": key_type,
        "key_display_suffix": "x7Qa",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
    }


@pytest.fixture
def as_jwt_user(monkeypatch):
    """Patch OIDC validation + DB lookups so 'Bearer jwt-token' resolves to the given user."""
    from core import security

    def _apply(user_id, roles, ngroups, privileges=None, name="Jane Doe"):
        monkeypatch.setattr(security.OIDCValidator, "validate_token",
                            lambda self, request, token: {"sub": str(user_id), "name": name})

        async def fake_details(conn, uid):
            return auth_details(roles, ngroups, privileges)

        monkeypatch.setattr(security.user_db, "get_user_auth_details", fake_details)
        return {"Authorization": "Bearer jwt-token"}

    return _apply


@pytest.fixture
def as_api_key(monkeypatch):
    """Patch API-key lookups so 'Bearer cue_sk_test' resolves to the given key row / user."""
    from core import security

    def _apply(row, user=None):
        async def fake_key(conn, key_hash):
            return row

        async def fake_user(conn, uid):
            return user

        monkeypatch.setattr(security.api_key_db, "get_user_from_api_key", fake_key)
        monkeypatch.setattr(security.user_db, "get_user_by_id", fake_user)
        return {"Authorization": "Bearer cue_sk_test"}

    return _apply
