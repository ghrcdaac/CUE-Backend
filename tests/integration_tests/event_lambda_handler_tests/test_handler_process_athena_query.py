import uuid
from test_loop_helper import run_handler
from structlog.testing import capture_logs

def test_process_athena_query_handler_query_succeeded(mock_lambda_context, mock_boto3_client):
    event = {"detail":{"currentState": "SUCCEEDED", "queryExecutionId":str(uuid.uuid4())}}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.process_athena_query.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "athena.query.succeeded"

def test_process_athena_query_handler_query_failed(mock_lambda_context, mock_boto3_client):
    event = {"detail":{"currentState":"FAILED", "queryExecutionId":str(uuid.uuid4())}}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.process_athena_query.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "athena.query.failed"

def test_process_athena_query_handler_query_other_state(mock_lambda_context, mock_boto3_client):
    event = {"detail":{"currentState":"RUNNING", "queryExecutionId":str(uuid.uuid4())}}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.process_athena_query.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "athena.query.state.ignored"