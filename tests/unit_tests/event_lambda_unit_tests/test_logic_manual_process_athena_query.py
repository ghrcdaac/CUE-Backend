import pytest
import uuid
from botocore.exceptions import ClientError
from app.event_lambdas.manual_process_athena_query.logic import validate_athena_query_details, check_result_exists, invoke_process_athena_query, ManualProcessAthenaQueryError
from app.event_lambdas.manual_process_athena_query.model import AthenaQueryDetails


@pytest.mark.asyncio
async def test_validate_athena_query_details(mock_boto3_client):
    """Test validating valid athena query details payload."""
    event_payload = {"current_state":"SUCCEEDED", "query_id":str(uuid.uuid4()), "user_id":uuid.uuid4()}
    details = await validate_athena_query_details(event_payload)
    assert isinstance(details, AthenaQueryDetails)

@pytest.mark.asyncio
async def test_validate_athena_query_details_fail(mock_boto3_client):
    """Test validating invalid athena query details payload."""
    #missing query_id
    event_payload = {"current_state":"SUCCEEDED", "user_id":uuid.uuid4()}
    with pytest.raises(ManualProcessAthenaQueryError):
        await validate_athena_query_details(event_payload)

@pytest.mark.asyncio
async def test_check_result_exists(mock_boto3_client):
    """Test checking result exists."""
    query_id = str(uuid.uuid4())
    success = await check_result_exists(query_id)
    assert success

@pytest.mark.asyncio
async def test_check_result_exists_fail(mock_boto3_client):
    """Test checking results exiss, buy athena client fails to get query execution."""
    athena = mock_boto3_client("athena")
    athena.get_query_execution.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_query_execution.failed"}}, operation_name="get_query_execution")
    query_id = str(uuid.uuid4())
    with pytest.raises(ManualProcessAthenaQueryError):
        await check_result_exists(query_id)

@pytest.mark.asyncio
async def test_invoke_process_athena_query(mock_boto3_client):
    """Test invoking process athena query."""
    current_state = "SUCCEEDED"
    query_id = str(uuid.uuid4())
    await invoke_process_athena_query(current_state, query_id)

@pytest.mark.asyncio
async def test_invoke_process_athena_query_fail(mock_boto3_client):
    """Test invoking process athena query, but it lambda client fails to invoke."""
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")
    current_state = "SUCCEEDED"
    query_id = str(uuid.uuid4())
    with pytest.raises(ManualProcessAthenaQueryError):
        await invoke_process_athena_query(current_state, query_id)