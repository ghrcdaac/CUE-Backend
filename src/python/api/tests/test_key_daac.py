"""Keys made for one DAAC only work in that DAAC (plan 23 B-K1, B-K2, B-K4)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import NGROUP_A, NGROUP_B, key_row, user_record
from test_upload_targets import fake_db  # noqa: F401  (fixture)
from test_api_key_validation import PRIVS, body, stored  # noqa: F401  (fixtures/helpers)
from v2.type_util.auth import AuthUser
from v2.utils import upload as upload_utils


def test_admin_with_a_daac_key_sees_only_that_daac(client, fake_db, as_api_key):  # noqa: F811
    uid = uuid.uuid4()
    k = key_row(user_id=uid, ngroup_id=NGROUP_A)
    r = client.get("/v2/me/upload-targets", headers=as_api_key(k, user_record(uid, ["admin"], [NGROUP_A, NGROUP_B])))
    assert r.status_code == 200, r.text
    assert fake_db["scope"] == "ngroups" and fake_db["ngroups"] == [NGROUP_A]
    assert r.json()["caller"]["key"]["ngroup"] == {"id": str(NGROUP_A), "short_name": "GHRC"}


def test_key_for_a_daac_the_user_left_is_403(client, fake_db, as_api_key):  # noqa: F811
    uid = uuid.uuid4()
    k = key_row(user_id=uid, ngroup_id=NGROUP_B)
    r = client.get("/v2/me/upload-targets", headers=as_api_key(k, user_record(uid, ["provider"], [NGROUP_A])))
    assert r.status_code == 403 and "no longer assigned" in r.json()["detail"]


def test_older_key_without_daac_keeps_full_access(client, fake_db, as_api_key):  # noqa: F811
    uid = uuid.uuid4()
    k = key_row(user_id=uid, ngroup_id=None)
    r = client.get("/v2/me/upload-targets", headers=as_api_key(k, user_record(uid, ["admin"], [NGROUP_A, NGROUP_B])))
    assert r.status_code == 200
    assert fake_db["scope"] == "all"
    assert r.json()["caller"]["key"]["ngroup"] is None


def test_jwt_admin_is_unchanged(client, fake_db, as_jwt_user):  # noqa: F811
    r = client.get("/v2/me/upload-targets", headers=as_jwt_user(uuid.uuid4(), ["admin"], [NGROUP_A]))
    assert r.status_code == 200 and fake_db["scope"] == "all"


def _user(**kw):
    return AuthUser(id=uuid.uuid4(), name="Jane", email="jane@example.com", roles=kw.get("roles", ["admin"]),
                    ngroups=[str(NGROUP_A)], key_ngroup_id=kw.get("key"))


def test_upload_check_blocks_other_daac_collections_even_for_admins():
    coll = {"ngroup_id": NGROUP_B}
    with pytest.raises(upload_utils.UploadValidationError, match="different DAAC"):
        upload_utils._check_key_daac(coll, "asdc_coll", _user(key=str(NGROUP_A)))
    upload_utils._check_key_daac({"ngroup_id": NGROUP_A}, "ghrc_coll", _user(key=str(NGROUP_A)))
    upload_utils._check_key_daac(coll, "asdc_coll", _user(key=None))  # signed in / older key: unchanged


@pytest.mark.parametrize("over", [
    {"expires_in_days": 91},
    {"expires_in_days": None, "expires_at": (datetime.now(timezone.utc) + timedelta(days=200)).isoformat()},
])
def test_new_keys_last_at_most_90_days(client, stored, as_jwt_user, over):  # noqa: F811
    h = as_jwt_user(uuid.uuid4(), ["provider"], [NGROUP_A], privileges=PRIVS)
    r = client.post("/v2/api-keys/", json={k: v for k, v in body(**over).items() if v is not None}, headers=h)
    assert r.status_code == 422, r.text
    assert stored == []


def test_90_day_key_still_allowed(client, stored, as_jwt_user):  # noqa: F811
    h = as_jwt_user(uuid.uuid4(), ["provider"], [NGROUP_A], privileges=PRIVS)
    r = client.post("/v2/api-keys/", json=body(expires_in_days=90), headers=h)
    assert r.status_code == 201, r.text
