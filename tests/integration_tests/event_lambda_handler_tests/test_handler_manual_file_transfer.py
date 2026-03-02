import pytest
import pytest_asyncio
import uuid
import json
from test_loop_helper import run_handler
from botocore.exceptions import ClientError

def test_manual_file_transfer_handler(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
    event = {"file_ids": test_files}
    print(event) 
    context = mock_lambda_context("cue_manual_file_transfer")
    from app.event_lambdas.manual_file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200

def test_manual_file_transfer_handler_empty_file_list(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {"file_ids": []}
    context = mock_lambda_context("cue_manual_file_transfer")
    from app.event_lambdas.manual_file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400

def test_manual_file_transfer_handler_empty_no_file_ids(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_manual_file_transfer")
    from app.event_lambdas.manual_file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400

def test_manual_file_transfer_handler_partial_success_files(test_admin_user, test_mix_files, mock_lambda_context, mock_boto3_client):
    event = {"file_ids": test_mix_files}
    context = mock_lambda_context("cue_manual_file_transfer")
    from app.event_lambdas.manual_file_transfer.handler import handler
    response = run_handler(handler, event, context)
    print(response)
    assert response["status_code"] == 207

def test_manual_file_transfer_handler_invalid_file_id(test_admin_user, mock_lambda_context, mock_boto3_client):
    event = {"file_ids": ["not_a_file_id"]}
    context = mock_lambda_context("cue_manual_file_transfer")
    from app.event_lambdas.manual_file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400

def test_manual_file_transfer_handler_no_db_pool(test_admin_user, test_files, mock_lambda_context, mock_boto3_client, mocker):
    event = {"file_ids": test_files}
    context = mock_lambda_context("cue_manual_file_transfer")
    mocker.patch("app.event_lambdas.manual_file_transfer.handler.get_database_pool", return_value=None)
    from app.event_lambdas.manual_file_transfer.handler import handler
    with pytest.raises(RuntimeError):
        run_handler(handler, event, context)

def test_manual_file_transfer_handler_cannot_verify_exists_in_s3(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
    s3 = mock_boto3_client("s3")
    s3.head_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"head_object.failed"}}, operation_name="head_object")
    event = {"file_ids": test_files}
    context = mock_lambda_context("cue_manual_file_transfer")
    from app.event_lambdas.manual_file_transfer.handler import handler
    response = run_handler(handler, event, context)
    print(response)
    assert response["status_code"] == 400

def test_manual_file_transfer_handler_cannot_send_message_to_sqs_queue(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
    sqs = mock_boto3_client("sqs")
    sqs.send_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"send_message.failed"}}, operation_name="send_message")
    event = {"file_ids": test_files}
    context = mock_lambda_context("cue_manual_file_transfer")
    from app.event_lambdas.manual_file_transfer.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400

@pytest_asyncio.fixture()
async def test_files(seed_file, test_provider_user):
    file_ids = []
    for i in range(1,4):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    return file_ids

@pytest_asyncio.fixture()
async def test_mix_files(seed_file, test_provider_user):
    file_ids = []
    # good files
    for i in range(1,4):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    #non candidate files for transfer 
    for i in range(1,2):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="distributed", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    for i in range(1,2):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="infected", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    for i in range(1,2):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="scan_failed", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    for i in range(1,2):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="uploading", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    for i in range(1,2):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="unscanned", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    # file does not exist in db
    for i in range(1,2):
        file_id = uuid.uuid4()
        file_ids.append(str(file_id))
    return file_ids