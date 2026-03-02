import pytest_asyncio
import pytest
import uuid 
from datetime import datetime, timezone, timedelta
from test_loop_helper import run_handler
from botocore.exceptions import ClientError

def test_cost_update_handler(mock_lambda_context, test_data, mock_boto3_client):
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)

    event = {"end_date": end_time.isoformat(), "start_date": start_time.isoformat()}
    context = mock_lambda_context("cue_cost_update")
    from app.event_lambdas.cost_update.handler import handler
    response = run_handler(handler, event, context) 
    assert response is None 

def test_cost_update_handler_no_data(mock_lambda_context, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_cost_update")
    from app.event_lambdas.cost_update.handler import handler
    response = run_handler(handler, event, context) 
    assert response is None

def test_cost_update_handler_cost_explorer_client_error(mock_lambda_context, test_data, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_cost_update")
    ce = mock_boto3_client("ce")
    ce.get_cost_and_usage.side_effect =  ClientError({"Error":{"Message":"Forced Error", "Code":"get_cost_and_usage.failed"}}, operation_name="get_cost_and_usage") 
    from app.event_lambdas.cost_update.handler import handler
    from app.event_lambdas.cost_update.logic import CostUpdateError
    with pytest.raises(CostUpdateError):
        run_handler(handler, event, context) 

def test_cost_update_handler_sts_client_error(mock_lambda_context, test_data, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_cost_update")
    sts = mock_boto3_client("sts")
    sts.assume_role.side_effect =  ClientError({"Error":{"Message":"Forced Error", "Code":"assume_role.failed"}}, operation_name="assume_role") 
    from app.event_lambdas.cost_update.handler import handler
    from app.event_lambdas.cost_update.logic import CostUpdateError
    with pytest.raises(CostUpdateError):
        run_handler(handler, event, context) 

@pytest_asyncio.fixture()
async def test_data(seed_file, test_admin_user):
    await seed_file(uuid.uuid4(),"file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(),"file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(),"file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")