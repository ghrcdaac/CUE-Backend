import pytest
from botocore.exceptions import ClientError

def test_email_sender_handler(mock_lambda_context, mock_boto3_client):
    """Test email sender handler - success."""
    event = {"recipients":["test@test.com"],
             "subject": "Hello World!",
             "body_html": "<html><p>Hello World!</p></html>",
             "body_text": "Hello World"}
    context = mock_lambda_context("cue_email_sender")
    from app.event_lambdas.email_sender.handler import handler
    response = handler(event, context)
    assert response.get("statusCode") == 200

def test_email_sender_handler_missing_email_subject(mock_lambda_context, mock_boto3_client):
    """Test email sender handler - missing subject."""
    event = {"recipients":["test@test.com"],
             "body_html": "<html><p>Hello World!</p></html>",
             "body_text": "Hello World"}
    context = mock_lambda_context("cue_email_sender")
    from app.event_lambdas.email_sender.handler import handler
    response = handler(event, context)
    assert response.get("statusCode") == 400

def test_email_sender_handler_client_error(mock_lambda_context, mock_boto3_client, mocker):
    """Test email sender handler - ses client failed to send email."""
    event = {"recipients":["test@test.com"],
             "subject": "Hello World!",
             "body_html": "<html><p>Hello World!</p></html>",
             "body_text": "Hello World"}
    context = mock_lambda_context("cue_email_sender")
    ses = mock_boto3_client("ses") 
    ses.send_email.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"send_email.failed"}}, operation_name="send_email")
    mocker.patch("app.event_lambdas.email_sender.handler.get_ses_client", return_value=ses)
    from app.event_lambdas.email_sender.handler import handler
    with pytest.raises(ClientError):
        handler(event, context)