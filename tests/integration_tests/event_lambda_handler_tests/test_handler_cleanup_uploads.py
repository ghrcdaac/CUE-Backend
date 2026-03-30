import pytest_asyncio
import pytest
import uuid 
from datetime import datetime

@pytest.mark.asyncio
async def test_cleanup_uploads_handler_all_uploads_with_data(mock_lambda_context, test_data, get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cleanup uploads handler - all uploads, db has data."""
    event = {"detail-type":"CleanupAllPendingUploads"}
    context = mock_lambda_context("cue_cleanup_uploads")
    mocker.patch("app.event_lambdas.cleanup_uploads.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cleanup_uploads.handler import async_handler
    response = await async_handler(event, context)
    assert response.get("status_code") == 200
    assert response.get("body").get("message") ==  "Successfully deleted pending uploads."

@pytest.mark.asyncio
async def test_cleanup_uploads_handler_all_uploads_no_data(mock_lambda_context, get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cleanup uploads handler - all uploads, db has no data."""
    event = {"detail-type":"CleanupAllPendingUploads"}
    context = mock_lambda_context("cue_cleanup_uploads")
    mocker.patch("app.event_lambdas.cleanup_uploads.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cleanup_uploads.handler import async_handler
    response = await async_handler(event, context)
    assert response.get("status_code") == 200
    assert response.get("body").get("message") == "There are no pending uploads to delete."

@pytest.mark.asyncio
async def test_cleanup_uploads_targeted_uploads_handler(mock_lambda_context, test_data, get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cleanup uploads - targeted success."""
    event = {"detail-type":"CleanupTargetedUploads", "query_parameters":{"end_date": datetime.now().date().strftime("%Y-%m-%d")}}
    context = mock_lambda_context("cue_cleanup_uploads")
    mocker.patch("app.event_lambdas.cleanup_uploads.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cleanup_uploads.handler import async_handler
    response = await async_handler(event, context)
    assert response.get("status_code") == 200
    assert response.get("body").get("message") == "Successfully deleted pending uploads."

@pytest.mark.asyncio
async def test_cleanup_uploads_targeted_uploads_handler_invalid_event(mock_lambda_context, test_data,  get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cleanup uploads - targeted failed validation"""  
    event = {"detail-type":"CleanupTargetedUploads"}
    context = mock_lambda_context("cue_cleanup_uploads")
    mocker.patch("app.event_lambdas.cleanup_uploads.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cleanup_uploads.handler import async_handler
    response = await async_handler(event, context) 
    assert response.get("status_code") == 400
    assert response.get("body").get("message") 

@pytest_asyncio.fixture()
async def test_data(seed_file, test_admin_user):
    await seed_file(uuid.uuid4(),"file1", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    await seed_file(uuid.uuid4(),"file2", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
    await seed_file(uuid.uuid4(),"file3", 'application/octet-stream', test_admin_user.id, 1024, status="uploading")
