"""Multipart/complete ownership (plan 11 B4.2): only whoever started the upload may continue it."""
import uuid

import pytest

from conftest import NGROUP_A, key_row, user_record
from v2.utils import upload as upload_utils

FILE_ID = uuid.uuid4()


class FakeS3:
    def generate_presigned_url(self, *a, **kw):
        return "https://s3.example/presigned"

    def complete_multipart_upload(self, **kw):
        return {}

    def abort_multipart_upload(self, **kw):
        return {}


@pytest.fixture
def upload_env(monkeypatch):
    state = {"owner": None}

    async def uploader(conn, file_id):
        return state["owner"] if file_id == FILE_ID else None

    async def ok(*a, **kw):
        return True

    async def allowed(request, name, user):
        return {"id": uuid.uuid4()}

    monkeypatch.setattr(upload_utils.file_db, "get_file_uploader", uploader)
    monkeypatch.setattr(upload_utils.file_db, "safely_advance_file_status", ok)
    monkeypatch.setattr(upload_utils.file_db, "update_final_file_details", ok)
    monkeypatch.setattr(upload_utils, "_validate_upload_permissions", allowed)
    monkeypatch.setattr(upload_utils, "_get_s3_client", lambda: FakeS3())
    return state


CALLS = [
    ("/v2/upload/multipart/get-part-url", {"file_id": str(FILE_ID), "upload_id": "u1", "part_number": 1}, 200),
    ("/v2/upload/multipart/complete", {"file_id": str(FILE_ID), "upload_id": "u1", "parts": [{"PartNumber": 1, "ETag": "e"}],
                                       "collection_name": "c1", "file_name": "a.nc", "content_type": "application/x-netcdf",
                                       "final_file_size": 10, "checksum": "abc", "collection_path": ""}, 200),
    ("/v2/upload/multipart/abort", {"file_id": str(FILE_ID), "upload_id": "u1"}, 204),
    ("/v2/upload/complete-single", {"file_id": str(FILE_ID), "s3_etag": "e"}, 200),
]


def _key(as_api_key, uid, roles=("provider",)):
    return as_api_key(key_row(user_id=uid), user_record(uid, list(roles), [NGROUP_A]))


@pytest.mark.parametrize("path,payload,ok_status", CALLS)
def test_owner_allowed(client, upload_env, as_api_key, path, payload, ok_status):
    uid = uuid.uuid4()
    upload_env["owner"] = uid
    r = client.post(path, json=payload, headers=_key(as_api_key, uid))
    assert r.status_code == ok_status, r.text


@pytest.mark.parametrize("path,payload,ok_status", CALLS)
def test_other_user_forbidden(client, upload_env, as_api_key, path, payload, ok_status):
    upload_env["owner"] = uuid.uuid4()
    r = client.post(path, json=payload, headers=_key(as_api_key, uuid.uuid4()))
    assert r.status_code == 403


@pytest.mark.parametrize("path,payload,ok_status", CALLS)
def test_admin_exempt(client, upload_env, as_api_key, path, payload, ok_status):
    upload_env["owner"] = uuid.uuid4()
    r = client.post(path, json=payload, headers=_key(as_api_key, uuid.uuid4(), roles=("admin",)))
    assert r.status_code == ok_status, r.text


def test_proxy_key_uses_creator_id(client, upload_env, as_api_key):
    creator = uuid.uuid4()
    upload_env["owner"] = creator
    k = key_row(user_id=None, key_type="proxy", proxy_user_name="Ingest Bot", created_by=creator)
    r = client.post(CALLS[0][0], json=CALLS[0][1], headers=as_api_key(k))
    assert r.status_code == 200, r.text


def test_unknown_file_forbidden(client, upload_env, as_api_key):
    uid = uuid.uuid4()
    upload_env["owner"] = uid
    payload = dict(CALLS[0][1], file_id=str(uuid.uuid4()))
    assert client.post(CALLS[0][0], json=payload, headers=_key(as_api_key, uid)).status_code == 403
