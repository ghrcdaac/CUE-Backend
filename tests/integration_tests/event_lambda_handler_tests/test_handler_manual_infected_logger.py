import pytest
import pytest_asyncio
import uuid
import json
from test_loop_helper import run_handler
from botocore.exceptions import ClientError

def test_manual_infected_logger_handler(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
    event = {"file_ids": test_files, "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_scan_event")
    messages = []
    for file_id in test_files:
        messages.append({"Body": json.dumps({"key": str(file_id)}), "ReceiptHandle":"mock_receipt_handle"})

    sqs = mock_boto3_client("sqs")
    sqs.receive_message.side_effect = None 
    sqs.receive_message.return_value = {"Messages": messages}

    from app.event_lambdas.manual_infected_logger.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200

def test_manual_infected_logger_handler_partial_success(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
    event = {"file_ids": test_files, "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_scan_event")
    messages = []
    # no message on dlq for last file_id
    for file_id in test_files[:-1]:
        messages.append({"Body": json.dumps({"key": str(file_id)}), "ReceiptHandle":"mock_receipt_handle"})

    sqs = mock_boto3_client("sqs")
    sqs.receive_message.side_effect = None 
    sqs.receive_message.return_value = {"Messages": messages}

    from app.event_lambdas.manual_infected_logger.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 207

def test_manual_infected_logger_handler_messages_not_on_dlq(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
    event = {"file_ids": test_files, "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_scan_event")
    from app.event_lambdas.manual_infected_logger.handler import handler
    response = run_handler(handler, event, context)
    print(response)
    assert response["status_code"] == 404

def test_manual_infected_logger_handler_no_db_pool(test_admin_user, test_files, mock_lambda_context, mock_boto3_client, mocker):
    event = {"file_ids": test_files, "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_scan_event")
    messages = []
    for file_id in test_files:
        messages.append({"Body": json.dumps({"key": str(file_id)}), "ReceiptHandle":"mock_receipt_handle"})

    sqs = mock_boto3_client("sqs")
    sqs.receive_message.side_effect = None 
    sqs.receive_message.return_value = {"Messages": messages}

    mocker.patch("app.event_lambdas.manual_infected_logger.handler.get_database_pool", return_value=None) 
    from app.event_lambdas.manual_infected_logger.handler import handler
    with pytest.raises(RuntimeError):
        run_handler(handler, event, context)

def test_manual_infected_logger_handler_messages_receive_message_from_dlq_client_error(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
    sqs = mock_boto3_client("sqs")
    sqs.receive_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"receive_message.failed"}}, operation_name="receive_message") 
    event = {"file_ids": test_files, "user_id":str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_scan_event")
    from app.event_lambdas.manual_infected_logger.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 404

def test_manual_infected_logger_handler_messages_send_message_to_scan_results_queue_client_error(test_admin_user, test_files, mock_lambda_context, mock_boto3_client):
     sqs = mock_boto3_client("sqs")
     sqs.send_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"send_message.failed"}}, operation_name="send_message") 
     sqs.delete_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"delete_message.failed"}}, operation_name="delete_message") 
     messages = []
     for file_id in test_files:
         messages.append({"Body": json.dumps({"key": str(file_id)}), "ReceiptHandle":"mock_receipt_handle"})

     sqs = mock_boto3_client("sqs")
     sqs.receive_message.side_effect = None 
     sqs.receive_message.return_value = {"Messages": messages}

     event = {"file_ids": test_files, "user_id":str(test_admin_user.id)}
     context = mock_lambda_context("cue_manual_scan_event")
     from app.event_lambdas.manual_infected_logger.handler import handler
     response = run_handler(handler, event, context)
     assert response["status_code"] == 500 

@pytest_asyncio.fixture()
async def test_files(seed_file, test_provider_user):
    file_ids = []
    for i in range(1,4):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_provider_user.id, 1024, status="unscanned", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids.append(str(file_id))
    return file_ids
