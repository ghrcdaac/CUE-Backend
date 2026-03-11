import pytest
import uuid


@pytest.mark.asyncio
async def test_existing_in_staging_exist(mock_boto3_client):
    """Test file exist in staging bucket."""
    from app.event_lambdas.manual_file_transfer.handler import exists_in_staging
    file_id = uuid.uuid4()
    exist = await exists_in_staging(file_id)
    assert exist

@pytest.mark.asyncio
async def test_existing_in_staging_does_not_exist(mock_boto3_client):
    """Test file does not exist in staging bucket."""
    from botocore.exceptions import ClientError
    s3 = mock_boto3_client('s3')
    s3.head_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"head_object.failed"}}, operation_name="head_object") 

    from app.event_lambdas.manual_file_transfer.handler import exists_in_staging

    file_id = uuid.uuid4()
    exist = await exists_in_staging(file_id)
    assert not exist