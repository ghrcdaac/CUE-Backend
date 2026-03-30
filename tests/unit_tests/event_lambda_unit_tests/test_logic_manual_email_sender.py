import pytest
import uuid
from botocore.exceptions import ClientError

@pytest.mark.asyncio
async def test_validate_email_payload(mock_boto3_client):
    """Test validating email payload."""
    from app.event_lambdas.manual_email_sender.logic import validate_email_payload
    from app.event_lambdas.manual_email_sender.model import EmailPayload
    payload = {"recipients": ["test_user@test.com"],
               "subject":"test_subject",
               "body_html":"<html><p>Test</p></html>",
               "body_text":"Test",
               "user_id":uuid.uuid4()}
    email_payload = await validate_email_payload(payload)
    assert isinstance(email_payload, EmailPayload)

@pytest.mark.asyncio
async def test_validate_email_payload_validation_invalid_payload(mock_boto3_client):
    """Test validating invalid email_payload"""
    from app.event_lambdas.manual_email_sender.logic import validate_email_payload, ManualEmailSenderError
    # Missing subject
    payload = {"recipients": ["test_user@test.com"],
               "body_html":"<html><p>Test</p></html>",
               "body_text":"Test",
               "user_id":uuid.uuid4()}
    with pytest.raises(ManualEmailSenderError):
        await validate_email_payload(payload)

@pytest.mark.asyncio
async def test_invoke_email_sender(mock_boto3_client):
    """Test invoking email sender."""
    from app.event_lambdas.manual_email_sender.logic import invoke_email_sender
    recipients = ["test_user@test.com"]
    subject = "test_subject"
    body_html = "<html><p>Test</p></html>"
    body_text = "Test"
    await invoke_email_sender(recipients, subject, body_html, body_text)


@pytest.mark.asyncio
async def test_invoke_email_sender_invoke_fail(mock_boto3_client):
    """Test invoking email sender, but lambda client fails to invoke."""
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")

    from app.event_lambdas.manual_email_sender.logic import invoke_email_sender, ManualEmailSenderError
    recipients = "test_user@test.com"
    subject = "test_subject"
    body_html = "<html><p>Test</p></html>"
    body_text = "Test"
    with pytest.raises(ManualEmailSenderError):
        await invoke_email_sender(recipients, subject, body_html, body_text)