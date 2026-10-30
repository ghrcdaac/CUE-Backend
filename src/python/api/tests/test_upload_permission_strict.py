"""Strict upload rule (plan 11 B3.5) as a pure function, plus the mode switch default. No DB needed."""
import uuid

import pytest

from v2.type_util.auth import AuthUser
from v2.utils import upload as upload_utils
from v2.utils.mappings import MappingBadRequest, assert_same_ngroup

G = uuid.uuid4()
COLLECTION = {"id": uuid.uuid4(), "short_name": "goesr_glm_l2", "ngroup_id": G, "active": True}


def user(roles, ngroups=(G,)):
    return AuthUser(id=uuid.uuid4(), roles=list(roles), ngroups=[str(n) for n in ngroups])


def rows(*items):
    return [{"provider_id": uuid.uuid4(), "can_upload": cu, "assigned": a} for cu, a in items]


def test_mode_defaults_to_legacy(monkeypatch):
    monkeypatch.delenv("UPLOAD_PROVIDER_CHECK_MODE", raising=False)
    assert upload_utils._check_mode() == "legacy"
    for value, expected in [("", "legacy"), ("LEGACY", "legacy"), ("bogus", "legacy"), ("strict", "strict"), (" Strict ", "strict")]:
        monkeypatch.setenv("UPLOAD_PROVIDER_CHECK_MODE", value)
        assert upload_utils._check_mode() == expected


def test_admin():
    assert upload_utils.strict_denial(COLLECTION, user(["admin"], []), rows((True, False))) is None
    assert upload_utils.strict_denial(COLLECTION, user(["admin"], []), rows((False, False)))[0] == "no_provider_allows_uploads"


@pytest.mark.parametrize("role", ["daac_manager", "daac_staff", "security", "proxy"])
def test_ngroup_wide_roles(role):
    assert upload_utils.strict_denial(COLLECTION, user([role]), rows((False, False), (True, False))) is None
    assert upload_utils.strict_denial(COLLECTION, user([role]), rows((False, False)))[0] == "no_provider_allows_uploads"
    assert upload_utils.strict_denial(COLLECTION, user([role], [uuid.uuid4()]), rows((True, False)))[0] == "group_mismatch"


def test_data_provider():
    dp = user(["provider"])
    assert upload_utils.strict_denial(COLLECTION, dp, rows((True, True))) is None
    reason, message = upload_utils.strict_denial(COLLECTION, dp, rows((True, False)))
    assert reason == "not_assigned_to_provider"
    assert message == "Upload Denied: you are not assigned to a provider for collection 'goesr_glm_l2'."
    reason, message = upload_utils.strict_denial(COLLECTION, dp, rows((False, True), (True, False)))
    assert message == "Upload Denied: none of the providers for collection 'goesr_glm_l2' allow uploads."
    assert upload_utils.strict_denial(COLLECTION, user(["provider"], [uuid.uuid4()]), rows((True, True)))[0] == "group_mismatch"


def test_assert_same_ngroup():
    assert_same_ngroup(G, [{"ngroup_id": G}, {"ngroup_id": str(G)}])
    with pytest.raises(MappingBadRequest, match="same DAAC"):
        assert_same_ngroup(G, [{"ngroup_id": G}, {"ngroup_id": uuid.uuid4()}])
