import pytest
import uuid
from structlog.testing import capture_logs

@pytest.mark.asyncio
async def test_process_athena_query_handler_query_succeeded(mock_lambda_context, mock_boto3_client):
    """Test process athena query handler - query SUCCEEDED"""
    event = {"detail":{"currentState": "SUCCEEDED", "queryExecutionId":str(uuid.uuid4())}}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.process_athena_query.handler import async_handler
    with capture_logs() as cap_logs:
        await async_handler(event,context)
    assert cap_logs[-1]["event"] == "athena.query.succeeded"

@pytest.mark.asyncio
async def test_process_athena_query_handler_query_failed(mock_lambda_context, mock_boto3_client):
    """Test process athena query handler - query failed"""
    event = {"detail":{"currentState":"FAILED", "queryExecutionId":str(uuid.uuid4())}}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.process_athena_query.handler import async_handler
    with capture_logs() as cap_logs:
        await async_handler(event,context)
    assert cap_logs[-1]["event"] == "athena.query.failed"

@pytest.mark.asyncio
async def test_process_athena_query_handler_query_other_state(mock_lambda_context, mock_boto3_client):
    """Test process athena query handler - query is other state besides FAILED or SUCCEEDED"""
    event = {"detail":{"currentState":"RUNNING", "queryExecutionId":str(uuid.uuid4())}}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.process_athena_query.handler import async_handler
    with capture_logs() as cap_logs:
        await async_handler(event,context)
    assert cap_logs[-1]["event"] == "athena.query.state.ignored"