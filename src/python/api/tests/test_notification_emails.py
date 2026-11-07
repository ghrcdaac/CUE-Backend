"""notification_manager emails (plan 28): environment, dashboard link, escaping. No DB, no AWS."""
import asyncio
import importlib
import json
import os
import sys
from pathlib import Path
from uuid import UUID

import pytest

NM_DIR = Path(__file__).resolve().parents[2] / "event_lambdas" / "notification_manager"
SECURITY = UUID("0259fb55-1146-4461-ade2-57504e0c3ace")
EVIL = '<a href="http://spam.example">click</a> & <b>x</b>'


class Ctx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def transaction(self):
        return Ctx()


class Pool:
    def acquire(self):
        return Ctx()


@pytest.fixture
def nm(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.setenv("APP_ENV", "uat")
    monkeypatch.setenv("FRONTEND_URL", "https://upload.uat.earthdata.nasa.gov/")
    monkeypatch.setenv("EMAIL_SENDER_ARN", "arn:test")
    monkeypatch.syspath_prepend(str(NM_DIR))
    for name in ("handler", "db", "logic"):
        sys.modules.pop(name, None)
    handler = importlib.import_module("handler")
    sent = []

    class FakeLambda:
        def invoke(self, **kw):
            sent.append(json.loads(kw["Payload"]))

    monkeypatch.setattr(handler, "lambda_client", FakeLambda())
    yield handler, sent
    for name in ("handler", "db", "logic"):
        sys.modules.pop(name, None)


def application(ngroup):
    async def fake(conn, app_id):
        return {"user_name": EVIL, "user_email": "a@example.com", "user_username": "u", "account_type": "provider",
                "justification": EVIL, "ngroup_id": ngroup, "ngroup_name": "CUE DAAC",
                "recipient_emails": ["staff@example.com"]}
    return fake


def assert_common(email, path):
    html, text = email["body_html"], email["body_text"]
    url = "https://upload.uat.earthdata.nasa.gov" + path
    assert email["subject"].startswith("[UAT] ")
    assert "<strong>Environment:</strong> UAT" in html
    assert f'href="{url}"' in html
    assert f"Environment: UAT\nCUE Dashboard: {url}" in text
    assert "{{" not in html
    for raw in ('<a href="http://spam', "<script>", "<img src=x>", "<b>prov</b>", "<b>x</b>"):
        assert raw not in html


@pytest.mark.parametrize("ngroup,idp,label", [(UUID(int=1), "google", "Google"), (SECURITY, None, "Unknown")])
def test_application_alerts(nm, ngroup, idp, label):
    handler, sent = nm
    handler.get_new_application_details = application(ngroup)
    detail = {"application_id": str(UUID(int=5))}
    if idp:
        detail["identity_provider"] = idp
    asyncio.run(handler.handle_application_submitted(detail, Pool()))
    assert_common(sent[0], "/users/pending-requests")
    assert f"<tr><th>Signed in with</th><td>{label}</td></tr>" in sent[0]["body_html"]
    assert "&lt;a href=&quot;http://spam.example&quot;&gt;" in sent[0]["body_html"]


def test_welcome(nm):
    handler, sent = nm

    async def fake(conn, uid):
        return {"user_name": "Pat", "user_email": "p@example.com"}

    handler.get_approved_user_details = fake
    asyncio.run(handler.handle_application_approved({"user_id": str(UUID(int=6))}, Pool()))
    assert_common(sent[0], "")
    assert sent[0]["subject"] == "[UAT] Welcome to the CUE System!"


def test_infected_report(nm):
    handler, sent = nm

    async def files(conn):
        return {"g1": {"short_name": "CUE", "recipient_emails": ["s@example.com"], "file_details": [
            {"file_id": "f1", "file_name": "<img src=x>.nc", "uploader_name": "u", "virusName": ["EICAR"]}]}}

    async def providers(conn, window, threshold):
        return {"g1": [{"provider_id": "p1", "provider_name": "<b>prov</b>", "is_currently_blocked": True,
                        "current_reason": "too many"}],
                "g2": [{"provider_id": "p2", "provider_name": "P2", "is_currently_blocked": False}]}

    async def mark(*args):
        return None

    async def recipients(conn, ngroup_id):
        return ["g2@example.com"], "G2"

    handler.get_infected_scheduled_file_details = files
    handler.get_providers_exceeding_threshold = providers
    handler.mark_files_as_notified = mark
    handler.mark_providers_as_notified = mark
    handler.get_ngroup_recipient_emails = recipients
    asyncio.run(handler.handle_infected_files_scheduled({}, Pool()))
    assert len(sent) == 2
    for email in sent:
        assert_common(email, "/files-by-status")
    assert "&lt;img src=x&gt;.nc" in sent[0]["body_html"]
    assert "<table>" in sent[0]["body_html"]  # our own table HTML is kept


def test_env_label_defaults(nm, monkeypatch):
    handler, _ = nm
    for value, label in [("prod", "PROD"), ("sit", "SIT"), ("", "LOCAL"), ("dev", "DEV")]:
        monkeypatch.setenv("APP_ENV", value)
        assert handler.env_label() == label
