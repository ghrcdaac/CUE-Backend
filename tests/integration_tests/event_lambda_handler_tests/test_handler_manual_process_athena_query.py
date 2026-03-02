import pytest
import uuid
from test_loop_helper import run_handler

def test_process_athena_query_handler_query_succeeded(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {"current_state": "SUCCEEDED", "query_id":str(uuid.uuid4()), "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.manual_process_athena_query.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200

def test_process_athena_query_handler_query_failed(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {"current_state":"FAILED", "query_id":str(uuid.uuid4()), "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.manual_process_athena_query.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200

def test_process_athena_query_handler_query_other_state(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {"current_state":"RUNNING", "query_id":str(uuid.uuid4()), "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_process_athena_query")
    from app.event_lambdas.manual_process_athena_query.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400