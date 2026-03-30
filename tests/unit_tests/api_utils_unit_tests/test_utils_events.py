import pytest
import uuid
import io
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from app.v2.utils.events import trigger_manual_file_transfer, EventError
from app.v2.type_util.events import FilePayload


@pytest.mark.asyncio
async def test_trigger_manual_file_transfer(test_admin_user, mock_boto3_client):
    """Test triggering a manual file transfer."""
    mock_file_payload = FilePayload(file_ids=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])

    response = await trigger_manual_file_transfer(mock_file_payload, test_admin_user)
    assert response["status_code"] == 200
    assert response["body"]["message"] == "All file transfers initiated."


@pytest.mark.asyncio
async def test_trigger_manual_file_transfer_invoke_fail(test_admin_user, mock_boto3_client):
    """Test triggering a manual file transfer, but the lambda function could not be invoked."""
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")

    mock_file_payload = FilePayload(file_ids=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    with pytest.raises(EventError):
        await trigger_manual_file_transfer(mock_file_payload, test_admin_user)

@pytest.mark.asyncio
async def test_trigger_manual_file_transfer_invalid_payload(test_admin_user, mock_boto3_client):
    """Test triggering a manual file transfer, but payload was invalid."""
    lambda_ = mock_boto3_client("lambda")
    payload_content = "string_to_fail"
    payload = StreamingBody(io.BytesIO(payload_content.encode()), len(payload_content.encode()))

    lambda_.invoke.side_effect = None
    lambda_.invoke.return_value = {"Payload": payload, "ResponseMetadata":{"RequestId": str(uuid.uuid4())}}

    mock_file_payload = FilePayload(file_ids=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    with pytest.raises(EventError):
        await trigger_manual_file_transfer(mock_file_payload, test_admin_user)

