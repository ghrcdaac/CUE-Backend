import pytest
from test_loop_helper import run_handler
from botocore.exceptions import ClientError

def test_manual_email_sender_handler(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = { "recipients":["test@test.com"], "subject":"Hello World", "body_html":"<html><p>Hello World!</p></html>", "body_text":"Hello World!", "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_email_sender.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200 

def test_manual_email_sender_handler_missing_email_component(test_admin_user, mock_lambda_context, mock_boto3_client):
    #even missing subject
    event = { "recipients":["test@test.com"], "body_html":"<html><p>Hello World!</p></html>", "body_text":"Hello World!", "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_email_sender.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400 
    
def test_manual_email_sender_handler_lambda_invoke_client_error(test_admin_user, mock_lambda_context, mock_boto3_client):
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")
    event = { "recipients":["test@test.com"], "subject":"Hello World", "body_html":"<html><p>Hello World!</p></html>", "body_text":"Hello World!", "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_cost_update")
    from app.event_lambdas.manual_email_sender.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 500 