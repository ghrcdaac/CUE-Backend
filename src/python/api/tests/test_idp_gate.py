"""Launchpad gate on user applications (plan 28). No DB needed."""
import uuid
from datetime import datetime, timezone

import pytest

from core import security
from v2.utils import idp_gate
from v2.utils import user_application as app_utils

from conftest import NGROUP_A, auth_details

SECURITY = idp_gate.ESDIS_SECURITY_NGROUP_ID
GATE_VARS = ("APPLICATION_IDP_GATE", "LAUNCHPAD_IDP_ALIASES", "APPLICATION_IDP_GATE_BYPASS_EMAILS", "APP_ENV")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in GATE_VARS:
        monkeypatch.delenv(name, raising=False)
    idp_gate._reported_users.clear()


def gate(monkeypatch, mode, bypass=None, app_env=None, aliases=None):
    monkeypatch.setenv("APPLICATION_IDP_GATE", mode)
    if bypass is not None:
        monkeypatch.setenv("APPLICATION_IDP_GATE_BYPASS_EMAILS", bypass)
    if app_env is not None:
        monkeypatch.setenv("APP_ENV", app_env)
    if aliases is not None:
        monkeypatch.setenv("LAUNCHPAD_IDP_ALIASES", aliases)


def check(idp, account_type="daac", ngroup=NGROUP_A, email="pat@example.com"):
    idp_gate.check_application(idp, email, uuid.uuid4(), account_type, ngroup)


# --- helper ----------------------------------------------------------------

def test_mode_defaults_to_off(monkeypatch):
    assert idp_gate.gate_mode() == "off"
    for value, expected in [("", "off"), ("bogus", "off"), ("LOG", "log"), (" Enforce ", "enforce")]:
        monkeypatch.setenv("APPLICATION_IDP_GATE", value)
        assert idp_gate.gate_mode() == expected


def test_launchpad_allow_list(monkeypatch):
    assert idp_gate.is_launchpad("launchpad")
    assert idp_gate.is_launchpad("Launchpad")
    for other in (None, "", "google", "edl", "earthdata", "launchpad-evil"):
        assert not idp_gate.is_launchpad(other)
    monkeypatch.setenv("LAUNCHPAD_IDP_ALIASES", "launchpad, launchpad-piv")
    assert idp_gate.is_launchpad("launchpad-piv")


def test_off_allows_everything():
    check("google", "daac")
    check(None, "provider", SECURITY)


@pytest.mark.parametrize("idp", ["google", "edl", None, "something-new"])
def test_enforce_non_launchpad(monkeypatch, idp):
    gate(monkeypatch, "enforce")
    check(idp, "provider")  # data provider is always fine
    with pytest.raises(idp_gate.IdpNotAllowedError):
        check(idp, "daac")
    with pytest.raises(idp_gate.IdpNotAllowedError):
        check(idp, "provider", SECURITY)
    with pytest.raises(idp_gate.IdpNotAllowedError):
        check(idp, "daac", SECURITY)


def test_enforce_launchpad_allowed(monkeypatch):
    gate(monkeypatch, "enforce")
    check("launchpad", "daac")
    check("launchpad", "provider")
    check("launchpad", "daac", SECURITY)


def test_log_mode_never_blocks(monkeypatch):
    gate(monkeypatch, "log")
    check("google", "daac")
    check("google", "provider", SECURITY)
    assert not idp_gate.provider_only("google", "pat@example.com")


def test_bypass_list(monkeypatch):
    gate(monkeypatch, "enforce", bypass="Tester@Example.com, other@example.com", app_env="uat")
    check("google", "daac", email="tester@example.com")
    check("google", "daac", email="TESTER@example.com")
    assert not idp_gate.provider_only("google", "tester@example.com")
    with pytest.raises(idp_gate.IdpNotAllowedError):
        check("google", "daac", email="someone@example.com")
    with pytest.raises(idp_gate.IdpNotAllowedError):
        check("google", "daac", email="example.com")  # no domain matches
    with pytest.raises(idp_gate.IdpNotAllowedError):
        check("google", "daac", email=None)


@pytest.mark.parametrize("prod", ["prod", "PROD", " prod "])
def test_bypass_ignored_in_prod(monkeypatch, prod):
    gate(monkeypatch, "enforce", bypass="tester@example.com", app_env=prod)
    with pytest.raises(idp_gate.IdpNotAllowedError):
        check("google", "daac", email="tester@example.com")
    assert idp_gate.provider_only("google", "tester@example.com")


def test_provider_only_flag(monkeypatch):
    assert not idp_gate.provider_only("google", "x@example.com")  # off
    gate(monkeypatch, "enforce")
    assert idp_gate.provider_only("google", "x@example.com")
    assert idp_gate.provider_only(None, "x@example.com")
    assert not idp_gate.provider_only("launchpad", "x@example.com")


@pytest.mark.parametrize("as_enum", [False, True])
def test_approval_rule(monkeypatch, as_enum):
    from v2.type_util.user_application import AccountType
    account_type = AccountType.PROVIDER if as_enum else "provider"  # stored value may be a str or the enum
    app = {"id": uuid.uuid4(), "account_type": account_type, "ngroup_id": NGROUP_A}
    idp_gate.check_approval(app, "daac_manager")  # off: unchanged behavior
    gate(monkeypatch, "log")
    idp_gate.check_approval(app, "daac_manager")
    gate(monkeypatch, "enforce")
    idp_gate.check_approval(app, "provider")
    for role in ("daac_manager", "daac_staff", "daac_observer", "admin", "security"):
        with pytest.raises(ValueError):
            idp_gate.check_approval(app, role)


def test_approval_rule_leaves_daac_and_security(monkeypatch):
    gate(monkeypatch, "enforce")
    idp_gate.check_approval({"account_type": "daac", "ngroup_id": NGROUP_A}, "daac_manager")
    idp_gate.check_approval({"account_type": "daac", "ngroup_id": NGROUP_A}, "admin")
    idp_gate.check_approval({"account_type": "provider", "ngroup_id": SECURITY}, "security")


def test_report_non_launchpad_privileged_logs_once(monkeypatch):
    calls = []
    monkeypatch.setattr(idp_gate.logger, "warning", lambda event, **kw: calls.append((event, kw)))
    uid = uuid.uuid4()
    idp_gate.report_non_launchpad_privileged(uid, "google", ["daac_observer"])  # off: nothing
    assert calls == []
    gate(monkeypatch, "log")
    idp_gate.report_non_launchpad_privileged(uid, "launchpad", ["admin"])
    idp_gate.report_non_launchpad_privileged(uuid.uuid4(), "google", ["provider"])
    assert calls == []
    idp_gate.report_non_launchpad_privileged(uid, "google", ["daac_observer"])
    idp_gate.report_non_launchpad_privileged(uid, "google", ["daac_observer"])
    assert [c[0] for c in calls] == ["auth.idp_gate.non_launchpad_privileged"]
    assert calls[0][1]["roles"] == ["daac_observer"]


# --- endpoints ---------------------------------------------------------------

def token_claims(monkeypatch, idp, email="pat@example.com", user_id=None):
    user_id = user_id or uuid.uuid4()
    payload = {"sub": str(user_id), "email": email, "name": "Pat", "preferred_username": "pat"}
    if idp is not None:
        payload["identity_provider"] = idp
    monkeypatch.setattr(security.OIDCValidator, "validate_token", lambda self, request, token: payload)
    return {"Authorization": "Bearer jwt-token"}, user_id


def application_body(account_type="daac", ngroup=NGROUP_A):
    body = {"email": "pat@example.com", "name": "Pat", "username": "pat", "justification": "work",
            "ngroup_id": str(ngroup), "account_type": account_type}
    if account_type == "provider":
        body["provider_id"] = str(uuid.uuid4())
    return body


@pytest.fixture
def submit_spy(monkeypatch):
    created, events = [], []

    async def fake_create(conn, app_data, user_id):
        created.append(user_id)
        return {"id": uuid.uuid4(), "user_id": user_id, "email": app_data.email, "name": app_data.name,
                "username": app_data.username, "justification": app_data.justification,
                "ngroup_id": app_data.ngroup_id, "provider_id": app_data.provider_id,
                "account_type": app_data.account_type.value, "edpub_id": None, "status": "pending",
                "is_spam": False, "applied": datetime.now(timezone.utc)}

    monkeypatch.setattr(app_utils.app_db, "create_user_application", fake_create)
    monkeypatch.setattr(app_utils, "publish_event", lambda **kw: events.append(kw))
    return created, events


def test_submit_denied_writes_nothing(monkeypatch, client, submit_spy):
    gate(monkeypatch, "enforce")
    headers, _ = token_claims(monkeypatch, "google")
    r = client.post("/v2/user_application/", json=application_body("daac"), headers=headers)
    assert r.status_code == 403
    assert "Launchpad" in r.json()["detail"]
    assert submit_spy == ([], [])


def test_submit_provider_allowed_and_event_has_idp(monkeypatch, client, submit_spy):
    gate(monkeypatch, "enforce")
    headers, user_id = token_claims(monkeypatch, "google")
    r = client.post("/v2/user_application/", json=application_body("provider"), headers=headers)
    assert r.status_code == 201, r.text
    created, events = submit_spy
    assert created == [user_id]
    assert events[0]["detail"]["identity_provider"] == "google"


def test_submit_launchpad_daac_allowed(monkeypatch, client, submit_spy):
    gate(monkeypatch, "enforce")
    headers, _ = token_claims(monkeypatch, "launchpad")
    assert client.post("/v2/user_application/", json=application_body("daac", SECURITY), headers=headers).status_code == 201


def test_submit_gate_off_unchanged(client, monkeypatch, submit_spy):
    headers, _ = token_claims(monkeypatch, None)
    assert client.post("/v2/user_application/", json=application_body("daac"), headers=headers).status_code == 201


@pytest.mark.parametrize("mode,idp,expected", [
    ("off", "google", False), ("log", "google", False), ("enforce", "google", True),
    ("enforce", None, True), ("enforce", "launchpad", False),
])
def test_status_reports_gate(monkeypatch, client, mode, idp, expected):
    gate(monkeypatch, mode)
    headers, _ = token_claims(monkeypatch, idp)

    async def fake_status(request, user_id):
        return "unregistered"

    from v2.endpoints import auth as auth_endpoints
    monkeypatch.setattr(auth_endpoints, "get_user_login_status", fake_status)
    body = client.get("/v2/auth/status", headers=headers).json()
    assert body == {"status": "unregistered", "idp_gate": mode, "provider_only": expected}


def test_approve_provider_application_with_daac_role_denied(monkeypatch, client):
    gate(monkeypatch, "enforce")
    approver = uuid.uuid4()
    monkeypatch.setattr(security.OIDCValidator, "validate_token",
                        lambda self, request, token: {"sub": str(approver), "identity_provider": "launchpad"})

    async def fake_details(conn, uid):
        return auth_details(["admin"], [NGROUP_A], ["application:approve"])

    async def fake_role(conn, role_id):
        return "daac_manager"

    async def fake_app(conn, app_id):
        return {"id": app_id, "status": "pending", "account_type": "provider", "ngroup_id": NGROUP_A,
                "user_id": uuid.uuid4(), "provider_id": uuid.uuid4()}

    monkeypatch.setattr(security.user_db, "get_user_auth_details", fake_details)
    monkeypatch.setattr(app_utils.role_db, "get_role_short_name_by_id", fake_role)
    monkeypatch.setattr(app_utils.app_db, "get_user_application_by_id", fake_app)
    r = client.post(f"/v2/user_application/{uuid.uuid4()}/approve",
                    params={"role_id": str(uuid.uuid4())}, headers={"Authorization": "Bearer jwt-token"})
    assert r.status_code == 403
    assert "provider" in r.json()["detail"]
