import pytest
import uuid
from pydantic import ValidationError
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.event_lambdas.cleanup_uploads.logic import validate_cleanup_event, get_upload_status_files, delete_upload_status_files
from app.event_lambdas.cleanup_uploads.model import CleanupPayload 

@pytest.mark.asyncio
async def test_validate_cleanup_event():
   mock_event = {"detail-type":"CleanupAllPendingUploads"} 
   valid_payload = await validate_cleanup_event(mock_event)
   assert CleanupPayload(**mock_event) == valid_payload

   mock_event = {"detail-type":"CleanupTargetedUploads", "query_parameters":{"end_date": datetime.now().date()}}
   valid_payload = await validate_cleanup_event(mock_event)
   assert CleanupPayload(**mock_event) == valid_payload

@pytest.mark.asyncio
async def test_validate_cleanup_event_fail():
    mock_event = {"detail-type":""}
    with pytest.raises(ValidationError):
        await validate_cleanup_event(mock_event)

    mock_event = {"detail-type":"CleanupTargetedUploads"}
    with pytest.raises(ValidationError):
        await validate_cleanup_event(mock_event)

@pytest.mark.asyncio
async def test_get_upload_status_files(seed_file, test_admin_user, connection_pool):
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")

    mock_event = {"detail-type":"CleanupAllPendingUploads"} 
    payload = CleanupPayload(**mock_event) 

    files = await get_upload_status_files(connection_pool, payload) 
    assert file_id1 in [f["id"] for f in files]
    assert file_id2 in [f["id"] for f in files]

    mock_event = {"detail-type":"CleanupTargetedUploads", "query_parameters":{"end_date": datetime.now().date()}}
    payload = CleanupPayload(**mock_event) 
    files2 = await get_upload_status_files(connection_pool, payload) 
    assert file_id1 in [f["id"] for f in files2]
    assert file_id2 in [f["id"] for f in files2]

@pytest.mark.asyncio
async def test_get_upload_status_files_cleanup_targeted_uploads_fail(seed_file, test_admin_user, connection_pool):
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")

    mock_event = {"detail-type":"CleanupTargetedUploads", "query_parameters":{"end_date": datetime.now().date()}}
    payload = CleanupPayload(**mock_event) 
    with patch("app.event_lambdas.cleanup_uploads.logic.get_upload_files") as get_uploads_mock:
        get_uploads_mock.side_effect=Exception("Forced DB Error")
        with pytest.raises(Exception):
            await get_upload_status_files(connection_pool, payload) 

@pytest.mark.asyncio
async def test_delete_upload_status_files(seed_file, test_admin_user, connection_pool):
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    files = [file_id1, file_id2]
     
    success = await delete_upload_status_files(connection_pool, files)
    assert success

@pytest.mark.asyncio
async def test_delete_upload_status_files_fail(seed_file, test_admin_user, connection_pool):
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    files = [file_id1, file_id2]
     
    with patch("app.event_lambdas.cleanup_uploads.logic.delete_upload_files") as delete_uploads_mock:
        delete_uploads_mock.side_effect=Exception("Forced DB Error")
        with pytest.raises(Exception):
            await delete_upload_status_files(connection_pool, files)