from datetime import datetime, timezone, timedelta
from test_loop_helper import run_handler
from botocore.exceptions import ClientError

def test_manual_cost_update_handler_with_range_params(test_admin_user, mock_lambda_context, mock_boto3_client):
    end_time = datetime.now(tz=timezone.utc) 
    start_time = end_time - timedelta(days=1)
    event = {"start_time": start_time.date() , "end_time": end_time.date(), "user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_cost_update.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200 

def test_manual_cost_update_handler_no_range_params(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {"user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_cost_update.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200 

def test_manual_cost_update_handler_with_bad_range_params(test_admin_user, mock_lambda_context, mock_boto3_client):
    # start_time after end_time
    start_time = datetime.now(tz=timezone.utc) 
    end_time = start_time - timedelta(days=1)
    event = {"start_time": start_time.date() , "end_time": end_time.date(), "user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_cost_update.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400 

def test_manual_cost_update_handler_empty_event(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_cost_update.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400 

def test_manual_cost_update_handler_lambda_invoke_client_error(test_admin_user, mock_lambda_context, mock_boto3_client):
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")
    end_time = datetime.now(tz=timezone.utc) 
    start_time = end_time - timedelta(days=1)
    event = {"start_time": start_time.date() , "end_time": end_time.date(), "user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_cost_update.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 500 