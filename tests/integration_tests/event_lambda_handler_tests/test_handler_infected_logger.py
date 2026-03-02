import pytest
import uuid 
import pytest_asyncio
import json
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from test_loop_helper import run_handler
from structlog.testing import capture_logs

def test_infected_logger_handler(mock_lambda_context, test_clean_records, mock_boto3_client):
    event = {"Records": test_clean_records }
    context = mock_lambda_context("cue_scan_event")

    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.success"

def test_infected_logger_handler_sqs_queue(mock_lambda_context, test_clean_records, mock_boto3_client, mocker):
    event = {"Records": test_clean_records }
    context = mock_lambda_context("cue_scan_event")
    mocker.patch("app.event_lambdas.infected_logger.logic.TRANSFER_INVOCATION_MODE", new="SQS")
    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.success"

def test_infected_logger_handler_no_records(mock_lambda_context, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_scan_event")
    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.no_valid_messages"

def test_infected_logger_handler_infected_records(mock_lambda_context, test_infected_records, mock_boto3_client):
    event = {"Records": test_infected_records}
    context = mock_lambda_context("cue_scan_event")
    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.success"

def test_infected_logger_handler_scan_failed_records(mock_lambda_context, test_scan_failed_records, mock_boto3_client):
    event = {"Records": test_scan_failed_records}
    context = mock_lambda_context("cue_scan_event")
    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.success"

def test_infected_logger_handler_bad_records(mock_lambda_context,  mock_boto3_client):
    event = {"Records": [{"body":"invalid_json"}, {"no_body":"body_of_message"}]  }
    context = mock_lambda_context("cue_scan_event")
    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.no_valid_messages"

def test_infected_logger_handler_lambda_invoke_client_error(mock_lambda_context, test_clean_records, mock_boto3_client, mocker):
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")
    mocker.patch("app.event_lambdas.infected_logger.logic.lambda_client", new=lambda_) 
    event = {"Records": test_clean_records }
    context = mock_lambda_context("cue_scan_event")
    from app.event_lambdas.infected_logger.handler import handler
    with pytest.raises(ClientError):
        run_handler(handler, event, context)

def test_infected_logger_handler_sqs_send_message_client_error(mock_lambda_context, test_clean_records, mock_boto3_client, mocker):
    event = {"Records": test_clean_records }
    context = mock_lambda_context("cue_scan_event")
    sqs = mock_boto3_client("sqs")
    sqs.send_message.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"send_message.failed"}}, operation_name="send_message") 
    mocker.patch("app.event_lambdas.infected_logger.logic.sqs_client", new=sqs) 
    mocker.patch("app.event_lambdas.infected_logger.logic.TRANSFER_INVOCATION_MODE", new="SQS")
    from app.event_lambdas.infected_logger.handler import handler
    with pytest.raises(ClientError):
        run_handler(handler, event, context)

def test_infected_logger_handler_no_db_pool(mock_lambda_context, test_clean_records, mock_boto3_client, mocker):
    event = {"Records": test_clean_records }
    context = mock_lambda_context("cue_scan_event")
    mocker.patch("app.event_lambdas.infected_logger.handler.get_database_pool", return_value=None)
    from app.event_lambdas.infected_logger.handler import handler
    with pytest.raises(RuntimeError):
        response = run_handler(handler, event, context)

def test_infected_logger_handler_no_transfer_queue(mock_lambda_context, test_clean_records, mock_boto3_client, mocker):
    event = {"Records": test_clean_records }
    context = mock_lambda_context("cue_scan_event")
    mocker.patch("app.event_lambdas.infected_logger.logic.TRANSFER_INVOCATION_MODE", new="SQS")
    mocker.patch("app.event_lambdas.infected_logger.logic.CLEAN_FILES_QUEUE_URL", new=None)
    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.success"

def test_infected_logger_handler_no_lambda(mock_lambda_context, test_clean_records, mock_boto3_client, mocker):
    event = {"Records": test_clean_records }
    context = mock_lambda_context("cue_scan_event")
    mocker.patch("app.event_lambdas.infected_logger.logic.FILE_TRANSFER_LAMBDA_NAME", new=None)
    from app.event_lambdas.infected_logger.handler import handler
    with capture_logs() as cap_logs:
        response = run_handler(handler, event, context)
    assert response is None
    assert cap_logs[-1]["event"] == "sqs.batch.success"

@pytest_asyncio.fixture()
async def test_clean_records(seed_file, test_collection, test_admin_user):
    records = []
    status = "clean"
    for i in range(1,4):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_admin_user.id, 1024, status=status, checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        record = {"messageId": str(uuid.uuid4()),
                  "body": make_scan_message_body(file_id, status)}
        records.append(record)
    return records

@pytest_asyncio.fixture()
async def test_infected_records(seed_file, test_collection, test_admin_user):
    records = []
    status = "infected"
    for i in range(1,6):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_admin_user.id, 1024, status=status, checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        record = {"messageId": str(uuid.uuid4()),
                  "body": make_scan_message_body(file_id, status)}
        records.append(record)
    return records

@pytest_asyncio.fixture()
async def test_scan_failed_records(seed_file, test_collection, test_admin_user):
    records = []
    status = "scan_failed"
    for i in range(1,6):
        file_id = uuid.uuid4()
        await seed_file(file_id, f"file{i}", 'application/octet-stream', test_admin_user.id, 1024, status=status, checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        record = {"messageId": str(uuid.uuid4()),
                  "body": make_scan_message_body(file_id, status)}
        records.append(record)
    return records

def make_scan_message_body(file_id, status):
    status_map = {"clean":"Clean", "infected":"Infected", "scan_failed":"Scan Failed"}
    id = uuid.uuid4()
    date_scanned = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    result = status_map.get(status)
    virus_name = json.dumps(["EICAR-AV-TEST"]) if status == "infected" else []

    body_str = f"""
         {{
             "id": "{id}",
             "guid": "{id}",
             "dateScanned": "{date_scanned}",
             "bucketName": "cue-sit-dmz",
             "name": "cue-sit-dmz",
             "key": "{file_id}",
             "versionId": null,
             "source": 0,
             "result": "{result}",
             "resultKind": "NotApplicable",
             "scanResults": [
                 {{
                     "result": "{result}",
                     "resultKind": "NotApplicable",
                     "virusName": {virus_name},
                     "message": [],
                     "dateScanned": "{date_scanned}",
                     "engine": "Sophos",
                     "trueFileType": "Octet-stream",
                     "engineVersion": "3.94.3",
                     "virusDbVersion": "6.21",
                     "scanType": "GoFwd"
                 }}
             ],
             "actionTaken": "None",
             "quarantineError": null,
             "virusUploadedBy": "",
             "fileExists": true,
             "fileSize": 1024,
             "movedTo": "cue-sit-staging/",
             "region": "us-west-2",
             "accountId": "123456780",
             "discoveredDate": "0001-01-01T00:00:00",
             "isProtected": false,
             "hasAVSchedule": 0,
             "isRealTimeClassificationEnabled": false,
             "hasClassifySchedule": 0,
             "resourceTypeName": "ScanResultLog",
             "orgId": null,
             "appId": "1234abc",
             "allowOnceExemptionAdded": false,
             "permanentlyAllowed": false,
             "accountIdResult": "1234567890#0",
             "staticAnalysisReport": null,
             "dynamicAnalysisReport": null,
             "bedrockAnalysisReport": null,
             "isWorkDocs": false
         }}
     """
    return body_str


