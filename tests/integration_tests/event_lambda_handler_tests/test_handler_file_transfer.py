import pytest
import pytest_asyncio
import uuid
import json
from test_loop_helper import run_handler
from botocore.exceptions import ClientError

def test_file_transfer_handler(mock_lambda_context, test_records_checksum, test_collection, mock_boto3_client):
    event = {"Records": test_records_checksum}
    context = mock_lambda_context("cue_file_transfer")
    from app.event_lambdas.file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response.get("batchItemFailures") == []

def test_file_transfer_handler_no_checksum(mock_lambda_context, test_records_no_checksum, test_collection, mock_boto3_client):
    event = {"Records": test_records_no_checksum}
    context = mock_lambda_context("cue_file_transfer")
    from app.event_lambdas.file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response.get("batchItemFailures") == []

def test_file_transfer_handler_no_records(mock_lambda_context, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_file_transfer")
    from app.event_lambdas.file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response.get("batchItemFailures") == []

def test_file_transfer_handler_no_pool(mock_lambda_context, test_records_checksum, test_collection, mock_boto3_client, mocker):
    records = test_records_checksum
    event = {"Records": records}
    context = mock_lambda_context("cue_file_transfer")
    mocker.patch("app.event_lambdas.file_transfer.handler.get_database_pool", return_value=None)
    from app.event_lambdas.file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert len(response.get("batchItemFailures")) > 0

def test_file_transfer_handler_bad_record(mock_lambda_context, test_records_checksum, test_collection, mock_boto3_client, mocker):
    records = test_records_checksum
    new_record = {"messageId": str(uuid.uuid4()),
                  "body": json.dumps({"file_id": str(uuid.uuid4()), "collection_id":str(test_collection['id'])})}
    records.append(new_record)
    event = {"Records": records}
    context = mock_lambda_context("cue_file_transfer")
    from app.event_lambdas.file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert len(response.get("batchItemFailures")) == 0

def test_file_transfer_handler_s3_copy_object_client_error(mock_lambda_context, test_records_checksum, test_collection, mock_boto3_client, mocker):
    event = {"Records": test_records_checksum}
    context = mock_lambda_context("cue_file_transfer")
    s3 = mock_boto3_client("s3")
    s3.copy_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"InternalError"}}, operation_name="copy_object") 
    mocker.patch("app.event_lambdas.file_transfer.logic.s3_client", new=s3)
    from app.event_lambdas.file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert len(response.get("batchItemFailures")) > 0

@pytest_asyncio.fixture()
async def test_records_checksum(seed_file, test_collection, test_admin_user):
    records = []
    for i in range(1,4):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        record = {"messageId": str(uuid.uuid4()),
                  "body": json.dumps({"file_id": str(file_id), "collection_id":str(test_collection['id'])})}
        records.append(record)
    return records

@pytest_asyncio.fixture()
async def test_records_no_checksum(seed_file, test_collection, test_admin_user):
    records = []
    for i in range(1,4):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
        record = {"messageId": str(uuid.uuid4()),
                  "body": json.dumps({"file_id": str(file_id), "collection_id":str(test_collection['id'])})}
        records.append(record)
    return records