import pytest
import uuid
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from app.event_lambdas.manual_cost_update.logic import validate_time_range, invoke_cost_update, ManualCostUpdateError
from app.event_lambdas.manual_cost_update.model import TimeRange

@pytest.mark.asyncio
async def test_validate_time_range():
    """Test validate time range."""
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1) 
    payload = {"start_time":start_time, "end_time":end_time, "user_id":uuid.uuid4()}
    result = await validate_time_range(payload)
    assert isinstance(result, TimeRange)

@pytest.mark.asyncio
async def test_validate_time_range_invalid_times():
    """Test validate time range invalid times."""
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1) 
    payload = {"start_time":start_time, "end_time":end_time}
    with pytest.raises(ManualCostUpdateError):
        await validate_time_range(payload)

@pytest.mark.asyncio
async def test_invoke_cost_update(mock_boto3_client):
    """Test invoke cost update."""
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1) 
    await invoke_cost_update(start_time, end_time)

@pytest.mark.asyncio
async def test_invoke_cost_update_fail(mock_boto3_client):
    """Test invoke cost update, but lambda client fails to invoke."""
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1) 
    with pytest.raises(ManualCostUpdateError):
        await invoke_cost_update(start_time, end_time)