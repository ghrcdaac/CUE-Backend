import pytest
import pytest_asyncio
import uuid
import json
from datetime import datetime, timezone
from test_loop_helper import run_handler 
from botocore.exceptions import ClientError

def test_manual_notification_manager_handler_user_application_submitted(test_admin_user, pending_application, mock_lambda_context, mock_boto3_client):
    event = {"detail-type":"UserApplicationSubmitted", "detail":{"application_id": str(pending_application["id"])}, "user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_notification_handler")
    from app.event_lambdas.manual_notification_manager.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200

def test_manual_notification_manager_handler_user_application_approved(test_admin_user, approved_user, mock_lambda_context, mock_boto3_client):
    event = {"detail-type":"UserApplicationApproved", "detail":{"user_id": str(approved_user)}, "user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_notification_handler")
    from app.event_lambdas.manual_notification_manager.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200


def test_manual_notification_manager_handler_infected_file(test_admin_user,test_infected_file, mock_lambda_context, mock_boto3_client):
    event ={"detail-type":"InfectedFileFound", "detail":{"key":str(test_infected_file)}, "user_id":str(test_admin_user.id)} 
    context = mock_lambda_context("cue_manual_notification_handler")
    from app.event_lambdas.manual_notification_manager.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 200

def test_manual_notification_manager_handler_empty_event(mock_lambda_context, mock_boto3_client):
    event = {}
    context = mock_lambda_context("cue_manual_notification_handler")
    from app.event_lambdas.manual_notification_manager.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 400

def test_manual_notification_manager_handler_user_application_submitted_lambda_invoke_client_error(test_admin_user, pending_application, mock_lambda_context, mock_boto3_client):
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")
    event = {"detail-type":"UserApplicationSubmitted", "detail":{"application_id": str(pending_application["id"])}, "user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_notification_handler")
    from app.event_lambdas.manual_notification_manager.handler import handler
    response = run_handler(handler, event, context)
    assert response["status_code"] == 500

def test_manual_notification_manager_handler_user_application_submitted_no_db_pool(test_admin_user, pending_application, mock_lambda_context, mock_boto3_client, mocker):
    event = {"detail-type":"UserApplicationSubmitted", "detail":{"application_id": str(pending_application["id"])}, "user_id": str(test_admin_user.id)}
    context = mock_lambda_context("cue_manual_notification_handler")
    mocker.patch("app.event_lambdas.manual_notification_manager.handler.get_database_pool", return_value=None)
    from app.event_lambdas.manual_notification_manager.handler import handler
    with pytest.raises(RuntimeError):
        run_handler(handler, event, context)

@pytest_asyncio.fixture()
async def pending_application(connection_pool, test_ngroup_id, test_provider):
    user_id = uuid.uuid4()
    query = """
        INSERT INTO user_application 
            (user_id, email, name, username, justification, ngroup_id, account_type, provider_id, edpub_id, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending')
        RETURNING *;
        """
    async with connection_pool.acquire() as conn:
        record = await conn.fetchrow(query, user_id, "user_application@test.com", "test userapp", "user_app_submit", "testing user app submit", test_ngroup_id, "provider", test_provider["id"], None)
    return record 

@pytest_asyncio.fixture()
async def approved_user(pending_application, test_ngroup_id, connection_pool):
    app_id = pending_application["id"]
    user_id = pending_application["user_id"]
    role_id = "2068cc53-1232-4bc7-9647-3e29e6418e21"
    async with connection_pool.acquire() as conn:
        await conn.fetchrow("INSERT INTO cueuser (id, email, name, cueusername, edpub_id) VALUES ($1, $2, $3, $4, $5) RETURNING *;",
        user_id, pending_application["email"], pending_application["name"], pending_application["username"], pending_application["edpub_id"])
        await conn.execute("INSERT INTO cueuser_role (cueuser_id, role_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, role_id)
        await conn.execute("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, test_ngroup_id)
        await conn.execute("UPDATE user_application SET status = $1 WHERE id = $2 RETURNING *;", "approved", app_id)
    return user_id 

@pytest_asyncio.fixture()
async def test_infected_file(seed_file, test_provider_user):
    file_id = uuid.uuid4()
    await seed_file(file_id, "file1", 'application/octet-stream', test_provider_user.id, 1024, status="infected", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=", scan_results = json.dumps([{"result": "Infected", "virusName":["EICAR-AV-TEST"], "message":["eicar.com"], "dateScanned":datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%I:%M:%S%fZ"), "engine":"Sophos"}]))
    return file_id