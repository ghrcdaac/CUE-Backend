import pytest
import uuid
import json
from botocore.exceptions import ClientError
from app.event_lambdas.manual_infected_logger.logic import validate_files, ManualInfectedLoggerError, poll_and_redrive

@pytest.mark.asyncio
async def test_validate_files(seed_file, connection_pool, test_admin_user, mock_boto3_client):
    file_ids = [uuid.uuid4() for i in range(0,4)]
    await seed_file(file_ids[0], "file1", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[1], "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    await seed_file(file_ids[2], "file3", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[3], "file4", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    payload = {"file_ids":file_ids, "user_id":test_admin_user.id}
    result = await validate_files(connection_pool, payload)
    print(result)
    print(file_ids)
    assert result[0] == [file_ids[0],file_ids[2]]
    assert result[1] == [str(file_ids[1]),str(file_ids[3])]

@pytest.mark.asyncio
async def test_validate_files_invalid_payload(seed_file, connection_pool, test_admin_user, mock_boto3_client):
    file_ids = [uuid.uuid4() for i in range(0,4)]
    await seed_file(file_ids[0], "file1", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[1], "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    await seed_file(file_ids[2], "file3", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[3], "file4", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    # no user_id
    payload = {"file_ids":file_ids}
    with pytest.raises(ManualInfectedLoggerError):
        await validate_files(connection_pool, payload)


@pytest.mark.asyncio
async def test_poll_and_redrive(seed_file, test_admin_user, mock_boto3_client):
    file_ids = [uuid.uuid4() for i in range(0,3)]
    messages = []
    for file_id in file_ids:
        messages.append({"Body": json.dumps({"key": str(file_id)}), "ReceiptHandle":"mock_receipt_handle"})

    sqs = mock_boto3_client("sqs")
    sqs.receive_message.side_effect = None 
    sqs.receive_message.return_value = {"Messages": messages}

    await seed_file(file_ids[0], "file1", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[1], "file2", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[2], "file3", 'application/octet-stream', test_admin_user.id, 1024)

    result = await poll_and_redrive(file_ids)
    assert result["moved_total"] == 3
    assert result["errors_total"] == 0
    assert result["not_redriven"] == []


@pytest.mark.asyncio
async def test_poll_and_redrive_empty_receives(seed_file, test_admin_user, mock_boto3_client):
    file_ids = [uuid.uuid4() for i in range(0,3)]
    sqs = mock_boto3_client("sqs")
    sqs.receive_message.side_effect = None 
    sqs.receive_message.return_value = {"Messages":[]}

    await seed_file(file_ids[0], "file1", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[1], "file2", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[2], "file3", 'application/octet-stream', test_admin_user.id, 1024)

    result = await poll_and_redrive(file_ids)
    assert result["moved_total"] == 0
    assert result["errors_total"] == 0
    assert result["not_redriven"] == sorted([str(file_id) for file_id in file_ids])


@pytest.mark.asyncio
async def test_poll_and_redrive_receive_message_fail(seed_file, test_admin_user, mock_boto3_client):
    file_ids = [uuid.uuid4() for i in range(0,3)]
    sqs = mock_boto3_client("sqs")
    sqs.receive_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"receive_message.failed"}}, operation_name="receive_message") 
    await seed_file(file_ids[0], "file1", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[1], "file2", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[2], "file3", 'application/octet-stream', test_admin_user.id, 1024)

    result = await poll_and_redrive(file_ids)
    assert result["moved_total"] == 0
    assert result["errors_total"] == 0
    assert result["not_redriven"] == sorted([str(file_id) for file_id in file_ids])

@pytest.mark.asyncio
async def test_poll_and_redrive_send_message_fail(seed_file, test_admin_user, mock_boto3_client):
    sqs = mock_boto3_client("sqs")
    file_ids = [uuid.uuid4() for i in range(0,3)]
    messages = []
    for file_id in file_ids:
        messages.append({"Body": json.dumps({"key": str(file_id)}), "ReceiptHandle":"mock_receipt_handle"})

    sqs.receive_message.side_effect = None
    sqs.receive_message.return_value = {"Messages":messages}
    sqs.send_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"send_message.failed"}}, operation_name="send_message") 

    await seed_file(file_ids[0], "file1", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[1], "file2", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[2], "file3", 'application/octet-stream', test_admin_user.id, 1024)

    result = await poll_and_redrive(file_ids)
    assert result["moved_total"] == 0
    assert result["errors_total"] > 0
    assert result["not_redriven"] == sorted([str(file_id) for file_id in file_ids])

@pytest.mark.asyncio
async def test_poll_and_redrive_delete_message_fail(seed_file, test_admin_user, mock_boto3_client):
    sqs = mock_boto3_client("sqs")
    file_ids = [uuid.uuid4() for i in range(0,3)]
    messages = []
    for file_id in file_ids:
        messages.append({"Body": json.dumps({"key": str(file_id)}), "ReceiptHandle":"mock_receipt_handle"})

    sqs.receive_message.side_effect = None
    sqs.receive_message.return_value = {"Messages":messages}
    sqs.delete_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"delete_message.failed"}}, operation_name="delete_message") 

    await seed_file(file_ids[0], "file1", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[1], "file2", 'application/octet-stream', test_admin_user.id, 1024)
    await seed_file(file_ids[2], "file3", 'application/octet-stream', test_admin_user.id, 1024)

    result = await poll_and_redrive(file_ids)
    assert result["moved_total"] == 0
    assert result["errors_total"] > 0 
    assert result["not_redriven"] == sorted([str(file_id) for file_id in file_ids])