import pytest
import pytest_asyncio
from typing import Tuple, Dict
from unittest.mock import patch, MagicMock
import uuid
import os
from botocore.exceptions import ClientError

from app.v2.utils.upload import prepare_single_file_upload, complete_single_file_upload, start_multipart_upload,  get_multipart_presigned_url, complete_multipart_upload, abort_multipart_upload, get_ip_address, _validate_upload_permissions, S3ClientError, UploadValidationError
from app.v2.type_util.upload import CompleteUploadRequest, MultipartGetPartUrlRequest, MultipartAbortRequest, PartInfo 
from app.v2.type_util.auth import AuthUser

@pytest.mark.asyncio
async def test_prepare_single_file_upload(make_request, connection_pool, test_admin_user, make_prepare_upload_request, mock_boto3_client):
    req = make_request()
    params = make_prepare_upload_request(file_size_bytes=1024)
    response = await prepare_single_file_upload(req, params, test_admin_user)
    file_id = response["file_id"]
    presigned_url = response["presigned_url"]
    assert presigned_url == "http://localhost/mock_presigned_url"
    assert isinstance(file_id, uuid.UUID)

    # Check DB
    async with connection_pool.acquire() as conn:
       file_id_db = await conn.fetchval("SELECT id FROM file WHERE id = $1;", file_id)
       file_status_db = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", file_id)
    assert file_id_db == file_id
    assert file_status_db == "uploading"

@pytest.mark.asyncio
async def test_prepare_single_file_upload_generate_presigned_url_fail(make_request, test_admin_user, make_prepare_upload_request, mock_boto3_client):
    s3 = mock_boto3_client("s3")
    s3.generate_presigned_url.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"generate_presigned_url.failed"}}, operation_name="generate_presigned_url")

    req = make_request()
    params = make_prepare_upload_request(file_size_bytes=1024)
    with pytest.raises(S3ClientError):
        await prepare_single_file_upload(req, params, test_admin_user)

@pytest.mark.asyncio
async def test_complete_single_upload(make_request, connection_pool,
                                     test_admin_user, make_prepare_upload_request,
                                     mock_boto3_client):
    req = make_request()
    req.state.pool = connection_pool

    prepare_params = make_prepare_upload_request(file_size_bytes=1024)
    response = await prepare_single_file_upload(req, prepare_params, test_admin_user)

    complete_params = CompleteUploadRequest(file_id=response["file_id"], s3_etag="<mock_md5_hash>")
    file_id = await complete_single_file_upload(req, complete_params,  test_admin_user)

    assert file_id == response["file_id"]
    assert response["presigned_url"] == "http://localhost/mock_presigned_url"

    # Check DB
    async with connection_pool.acquire() as conn:
       file_id_db = await conn.fetchval("SELECT id FROM file WHERE id = $1;", file_id)
       file_status_db = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", file_id)
    assert file_id_db == file_id
    assert file_status_db == "unscanned"

@pytest.mark.asyncio
async def test_start_multipart_upload(make_request, connection_pool, make_multipart_start_request, test_admin_user, mock_boto3_client):
    req = make_request()
    req.state.pool = connection_pool

    params = make_multipart_start_request(final_file_size_bytes=1024*1024*1024)

    response = await start_multipart_upload(req, params, test_admin_user)
    file_id = response["file_id"]
    upload_id = response["upload_id"]
    assert isinstance(file_id, uuid.UUID)
    assert upload_id == "mock_upload_id"

    # Check DB
    async with connection_pool.acquire() as conn:
       file_id_db = await conn.fetchval("SELECT id FROM file WHERE id = $1;", file_id)
       file_status_db = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", file_id)
    assert file_id_db == file_id
    assert file_status_db == "uploading"

@pytest.mark.asyncio
async def test_start_multipart_upload_create_multipart_upload_fail(make_request, connection_pool, make_multipart_start_request, test_admin_user, mock_boto3_client):
    s3 = mock_boto3_client("s3")
    s3.create_multipart_upload.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"create_multipart_upload.failed"}}, operation_name="create_multipart_upload")

    req = make_request()
    req.state.pool = connection_pool

    params = make_multipart_start_request(final_file_size_bytes=1024*1024*1024)

    with pytest.raises(S3ClientError):
        await start_multipart_upload(req, params, test_admin_user)


@pytest.mark.asyncio
async def test_get_multipart_presigned_url(make_request, connection_pool, make_multipart_start_request, test_admin_user, mock_boto3_client):
    req = make_request()
    req.state.pool = connection_pool

    start_params = make_multipart_start_request(final_file_size_bytes=1024*1024*1024)
    start_response = await start_multipart_upload(req, start_params, test_admin_user)
    file_id = start_response["file_id"]
    upload_id = start_response["upload_id"]
    part_number = 1

    get_part_params = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=part_number) 
    get_part_response = await get_multipart_presigned_url(get_part_params)
    assert get_part_response["presigned_url"] == "http://localhost/mock_presigned_url"


@pytest.mark.asyncio
async def test_get_multipart_presigned_url_generate_presigned_url_fail(make_request, connection_pool, make_multipart_start_request, test_admin_user, mock_boto3_client):
    req = make_request()

    s3 = mock_boto3_client("s3")
    s3.generate_presigned_url.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"generate_presigned_url.failed"}}, operation_name="generate_presigned_url")

    start_params = make_multipart_start_request(final_file_size_bytes=1024*1024*1024)
    start_response = await start_multipart_upload(req, start_params, test_admin_user)
    file_id = start_response["file_id"]
    upload_id = start_response["upload_id"]
    part_number = 1

    get_part_params = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=part_number) 
    with pytest.raises(S3ClientError):
        await get_multipart_presigned_url(get_part_params)

@pytest.mark.asyncio
async def test_complete_multipart_upload(make_request, connection_pool, make_multipart_start_request, make_multipart_complete_request, test_admin_user, mock_boto3_client):
    req = make_request()
    file_size_bytes = 1024*1024*1024 
    start_params = make_multipart_start_request(final_file_size_bytes=file_size_bytes)
    start_response = await start_multipart_upload(req, start_params, test_admin_user)
    file_id = start_response["file_id"]
    upload_id = start_response["upload_id"]

    part_params1 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 
    part_params2 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 

    await get_multipart_presigned_url(part_params1)
    await get_multipart_presigned_url(part_params2)

    parts = [PartInfo(PartNumber=1, ETag="mock_Etag1"),
             PartInfo(PartNumber=2, ETag="mock_Etag2")]

    complete_params = make_multipart_complete_request(file_id, upload_id, parts, final_file_size=file_size_bytes)

    response_file_id = await complete_multipart_upload(req, complete_params, test_admin_user)
    assert response_file_id == file_id 

    # Check DB
    async with connection_pool.acquire() as conn:
       file_id_db = await conn.fetchval("SELECT id FROM file WHERE id = $1;", file_id)
       file_status_db = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", file_id)
    assert file_id_db == file_id
    assert file_status_db == "unscanned"

@pytest.mark.asyncio
async def test_complete_multipart_upload_fail(make_request, connection_pool, make_multipart_start_request, make_multipart_complete_request, test_admin_user, mock_boto3_client):
    req = make_request()
    s3 = mock_boto3_client("s3")
    s3.complete_multipart_upload.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"complete_multipart_upload.failed"}}, operation_name="complete_multipart_upload")

    file_size_bytes = 1024*1024*1024 
    start_params = make_multipart_start_request(final_file_size_bytes=file_size_bytes)
    start_response = await start_multipart_upload(req, start_params, test_admin_user)
    file_id = start_response["file_id"]
    upload_id = start_response["upload_id"]

    part_params1 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 
    part_params2 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 

    await get_multipart_presigned_url(part_params1)
    await get_multipart_presigned_url(part_params2)

    parts = [PartInfo(PartNumber=1, ETag="mock_Etag1"),
             PartInfo(PartNumber=2, ETag="mock_Etag2")]

    complete_params = make_multipart_complete_request(file_id, upload_id, parts, final_file_size=file_size_bytes)

    with pytest.raises(S3ClientError):
        await complete_multipart_upload(req, complete_params, test_admin_user)

@pytest.mark.asyncio
async def test_abort_multipart_upload(make_request, connection_pool, make_multipart_start_request, test_admin_user, mock_boto3_client):
    req = make_request()
    req.state.pool = connection_pool

    start_params = make_multipart_start_request(final_file_size_bytes=1024*1024*1024)
    start_response = await start_multipart_upload(req, start_params, test_admin_user)
    file_id = start_response["file_id"]
    upload_id = start_response["upload_id"]

    part_params1 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 
    part_params2 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 

    await get_multipart_presigned_url(part_params1)
    await get_multipart_presigned_url(part_params2)

    params = MultipartAbortRequest(file_id=file_id, upload_id=upload_id)
    await abort_multipart_upload(params)

@pytest.mark.asyncio
async def test_abort_multipart_upload_abort_multipart_upload_not_found(make_request, connection_pool, make_multipart_start_request, test_admin_user, mock_boto3_client):
    s3 = mock_boto3_client("s3")
    s3.abort_multipart_upload.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"NoSuchUpload"}}, operation_name="abort_multipart_upload")
    req = make_request()
    req.state.pool = connection_pool

    start_params = make_multipart_start_request(final_file_size_bytes=1024*1024*1024)
    start_response = await start_multipart_upload(req, start_params, test_admin_user)
    file_id = start_response["file_id"]
    upload_id = start_response["upload_id"]

    part_params1 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 
    part_params2 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 

    await get_multipart_presigned_url(part_params1)
    await get_multipart_presigned_url(part_params2)

    params = MultipartAbortRequest(file_id=file_id, upload_id=upload_id)
    await abort_multipart_upload(params)

@pytest.mark.asyncio
async def test_abort_multipart_upload_abort_multipart_upload_failed(make_request, connection_pool, make_multipart_start_request, test_admin_user, mock_boto3_client):
    s3 = mock_boto3_client("s3")
    s3.abort_multipart_upload.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"abort_multipart_upload.failed"}}, operation_name="abort_multipart_upload")
    req = make_request()
    req.state.pool = connection_pool

    start_params = make_multipart_start_request(final_file_size_bytes=1024*1024*1024)
    start_response = await start_multipart_upload(req, start_params, test_admin_user)
    file_id = start_response["file_id"]
    upload_id = start_response["upload_id"]

    part_params1 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 
    part_params2 = MultipartGetPartUrlRequest(file_id=file_id, upload_id=upload_id, part_number=1) 

    await get_multipart_presigned_url(part_params1)
    await get_multipart_presigned_url(part_params2)

    params = MultipartAbortRequest(file_id=file_id, upload_id=upload_id)
    with pytest.raises(S3ClientError):
        await abort_multipart_upload(params)

@pytest.mark.asyncio
async def test_get_ip_address(make_request):
    req = make_request()
    ip_address = await get_ip_address(req)
    assert ip_address == req.client.host or str(req.headers.get("x-forwarded-for","").split(",")[0])

@pytest.mark.asyncio
async def test_validate_upload_permissions_collection_does_not_exist(make_request, test_provider_user):
    req = make_request()

    with pytest.raises(UploadValidationError):
        await _validate_upload_permissions(req, "not_a_valid_collection", test_provider_user)

@pytest.mark.asyncio
async def test_validate_upload_permissions_provider_cannot_upload(make_request, connection_pool, test_collection, test_provider, test_provider_user):
    req = make_request()

    async with connection_pool.acquire() as conn:
        await conn.execute("UPDATE provider SET can_upload = FALSE WHERE id = $1", test_provider["id"])

    with pytest.raises(UploadValidationError):
        await _validate_upload_permissions(req, test_collection["short_name"], test_provider_user)

@pytest.mark.asyncio
async def test_validate_upload_permissions_incorrect_group(make_request, seed_ngroup, seed_provider, seed_egress, seed_collection, test_provider, test_admin_user, test_provider_user):
    req = make_request()

    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")

    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup_id2)
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup_id2)
    test_collection2 = await seed_collection("test_collection2", True, provider_id=provider2["id"], egress_id=egress2["id"], ngroup_id=ngroup_id2)

    with pytest.raises(UploadValidationError):
        await _validate_upload_permissions(req, test_collection2["short_name"], test_provider_user)