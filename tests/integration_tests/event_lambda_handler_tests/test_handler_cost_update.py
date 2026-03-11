import pytest_asyncio
import pytest
import uuid 
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from structlog.testing import capture_logs
 
@pytest.mark.asyncio
async def test_cost_update_handler(mock_lambda_context, test_data, get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cost update handler - success"""
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)

    event = {"end_date": end_time.isoformat(), "start_date": start_time.isoformat()}
    context = mock_lambda_context("cue_cost_update")
    mocker.patch("app.event_lambdas.cost_update.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    mocker.patch("app.event_lambdas.cost_update.logic.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cost_update.handler import async_handler
    with capture_logs() as cap_logs:
        response = await async_handler(event, context) 
    assert response is None
    assert cap_logs[-1]["event"].startswith("Finished updating files between")

@pytest.mark.asyncio
async def test_cost_update_handler_no_data(mock_lambda_context, get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cost update handler with no data - success"""
    event = {}
    context = mock_lambda_context("cue_cost_update")
    mocker.patch("app.event_lambdas.cost_update.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    mocker.patch("app.event_lambdas.cost_update.logic.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cost_update.handler import async_handler
    with capture_logs() as cap_logs:
        response = await async_handler(event, context)
    assert response is None
    assert cap_logs[-1]["event"].startswith("Finished updating files between")

@pytest.mark.asyncio
async def test_cost_update_handler_cost_explorer_client_error(mock_lambda_context, test_data, get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cost update handler - cost explorer client fails to get cost and usage."""
    event = {}
    context = mock_lambda_context("cue_cost_update")
    ce = mock_boto3_client("ce")
    ce.get_cost_and_usage.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_cost_and_usage.failed"}}, operation_name="get_cost_and_usage") 
    mocker.patch("app.event_lambdas.cost_update.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    mocker.patch("app.event_lambdas.cost_update.logic.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cost_update.handler import async_handler
    from app.event_lambdas.cost_update.logic import CostUpdateError
    with pytest.raises(CostUpdateError):
        await async_handler(event,context)

@pytest.mark.asyncio
async def test_cost_update_handler_sts_client_error(mock_lambda_context, test_data, get_database_pool, mocker, mock_boto3_client, patch_loop):
    """Test cost update handler - sts client fails to assume role."""
    event = {}
    context = mock_lambda_context("cue_cost_update")
    sts = mock_boto3_client("sts")
    sts.assume_role.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"assume_role.failed"}}, operation_name="assume_role") 
    mocker.patch("app.event_lambdas.cost_update.handler.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    mocker.patch("app.event_lambdas.cost_update.logic.get_database_pool", new_callable=mocker.AsyncMock, return_value=get_database_pool)
    from app.event_lambdas.cost_update.handler import async_handler
    from app.event_lambdas.cost_update.logic import CostUpdateError
    with pytest.raises(CostUpdateError):
        await async_handler(event, context)

@pytest_asyncio.fixture()
async def test_data(seed_file, test_admin_user):
    await seed_file(uuid.uuid4(),"file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(),"file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(),"file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")