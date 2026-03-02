import pytest
import pytest_asyncio
import json
import uuid
import random
import os
from datetime import datetime, timezone, timedelta
from test_loop_helper import run_handler
from structlog.testing import capture_logs

def test_notification_manager_handler_infected_file_found(mock_lambda_context, mock_boto3_client):
    event = {"detail-type":"InfectedFileFound" , "detail": {"key":str(uuid.uuid4())}}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "db.pool.initialized_successfully"

def test_notification_manager_handler_other_event_type(mock_lambda_context, mock_boto3_client):
    event = {"detail-type":"OtherNotificationEvent" , "detail": {}}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "event.unhandled_type" 

def test_notification_manager_handler_scheduled_infected_files_provider_block(mock_lambda_context, block_test_provider_with_files, mock_boto3_client):
    event = {"detail-type":"ScheduledInfectedFileFound" , "detail": datetime.now(tz=timezone.utc).isoformat()}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "email_sender.invoke.started" 

def test_notification_manager_handler_scheduled_infected_files_no_provider_block(mock_lambda_context, infected_files_no_provider_block, mock_boto3_client):
    event = {"detail-type":"ScheduledInfectedFileFound" , "detail": datetime.now(tz=timezone.utc).isoformat()}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "email_sender.invoke.started" 

def test_notification_manager_handler_scheduled_infected_files_provider_block_only(mock_lambda_context, block_test_provider_files_previously_notified, mock_boto3_client):
    event = {"detail-type":"ScheduledInfectedFileFound" , "detail": datetime.now(tz=timezone.utc).isoformat()}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "email_sender.invoke.started" 

def test_notification_manager_handler_scheduled_infected_files_no_op(mock_lambda_context, mock_boto3_client):
    event = {"detail-type":"ScheduledInfectedFileFound" , "detail": datetime.now(tz=timezone.utc).isoformat()}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "No new infected files or provider blocks to report." 

def test_notification_manager_handler_application_submitted(mock_lambda_context, pending_user, test_admin_user, test_daac_manager_user, mock_boto3_client):
    event = {"detail-type":"UserApplicationSubmitted" , "detail":{"application_id": str(pending_user["id"])}}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "email_sender.invoke.started" 

def test_notification_manager_handler_application_submitted_application_does_not_exist(mock_lambda_context, pending_user, test_admin_user, test_daac_manager_user, mock_boto3_client):
    event = {"detail-type":"UserApplicationSubmitted" , "detail":{"application_id": str(uuid.uuid4())}}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "notification.recipients.not_found" 

def test_notification_manager_handler_application_approved(mock_lambda_context, approved_user, test_admin_user, test_daac_manager_user, mock_boto3_client):
    event = {"detail-type":"UserApplicationApproved" , "detail":{"user_id": str(approved_user)}}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "email_sender.invoke.started" 

def test_notification_manager_handler_application_approved_user_does_not_exist(mock_lambda_context, approved_user, test_admin_user, test_daac_manager_user, mock_boto3_client):
    event = {"detail-type":"UserApplicationApproved" , "detail":{"user_id": str(uuid.uuid4())}}
    context = mock_lambda_context("cue_notification_manager")
    from app.event_lambdas.notification_manager.handler import handler
    with capture_logs() as cap_logs:
        run_handler(handler, event, context)
    assert cap_logs[-1]["event"] == "notification.user_details.not_found" 

@pytest_asyncio.fixture()
async def pending_user(connection_pool, test_ngroup_id, test_provider):
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
async def approved_user(pending_user, test_ngroup_id, connection_pool):
    user_id = pending_user["user_id"]
    role_id = "2068cc53-1232-4bc7-9647-3e29e6418e21"
    async with connection_pool.acquire() as conn:
        await conn.fetchrow("INSERT INTO cueuser (id, email, name, cueusername, edpub_id) VALUES ($1, $2, $3, $4, $5) RETURNING *;",
        user_id, pending_user["email"], pending_user["name"], pending_user["username"], pending_user["edpub_id"])
        await conn.execute("INSERT INTO cueuser_role (cueuser_id, role_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, role_id)
        await conn.execute("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, test_ngroup_id)
        await conn.execute("UPDATE user_application SET status = $1 WHERE id = $2 RETURNING *;", "approved", user_id)
    return user_id 

@pytest_asyncio.fixture()
async def test_infected_files(seed_file, test_collection, test_provider_user):
    async def _test_infected_files(num_files, notification_sent_at=None):
        status = "infected"
        for i in range(1,num_files+1):
            upload_time = datetime.now(tz=timezone.utc) - timedelta(hours=8)
            scan_start = upload_time + timedelta(milliseconds=5)
            scan_end = scan_start + timedelta(milliseconds=random.randint(10,30))
            file_id = uuid.uuid4()
            await seed_file(file_id,
                            f"file{i}",
                            'application/octet-stream',
                            test_provider_user.id,
                            1024,
                            upload_time=upload_time,
                            scan_start=scan_start,
                            scan_end=scan_end,
                            status=status,
                            checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=",
                            scan_results = json.dumps([{"result": "Infected",
                                            "virusName":["EICAR-AV-TEST"],
                                            "message":["eicar.com"],
                                            "dateScanned":scan_end.strftime("%Y-%m-%dT%I:%M:%S%fZ"),
                                            "engine":"Sophos"}]),
                            notification_sent_at=notification_sent_at
            )
    return _test_infected_files 

@pytest_asyncio.fixture()
async def infected_files_no_provider_block(test_infected_files):
    infected_file_threshold = int(os.getenv("INFECTED_FILE_THRESHOLD", "5"))
    await test_infected_files(infected_file_threshold-1)

@pytest_asyncio.fixture()
async def block_test_provider_files_previously_notified(test_provider, test_infected_files, connection_pool):
    infected_file_threshold = int(os.getenv("INFECTED_FILE_THRESHOLD", "5"))
    await test_infected_files(infected_file_threshold, notification_sent_at=datetime.now(tz=timezone.utc) - timedelta(minutes=30))
    async with connection_pool.acquire() as conn:
        query = """
            UPDATE provider
            SET 
                can_upload = false,
                reason = $2
            WHERE id = $1 AND can_upload = true 
            """
        await conn.execute(query, test_provider["id"], "testing provider block email")

@pytest_asyncio.fixture()
async def block_test_provider_with_files(test_provider, connection_pool, test_infected_files):
    infected_file_threshold = int(os.getenv("INFECTED_FILE_THRESHOLD", "5"))
    blocking_lookback_hours = int(os.getenv("BLOCKING_LOOKBACK_HOURS", "24"))
    lookback_window = timedelta(hours=blocking_lookback_hours)
    await test_infected_files(infected_file_threshold)
    blocked = False
    query = """
        SELECT COUNT(f.id)
        FROM file f
        JOIN file_status fs ON f.id = fs.id
        JOIN collection c ON f.collection_id = c.id 
        WHERE c.provider_id = $1
          AND fs.status = 'infected'
          AND fs.scan_end >= (NOW() - $2::INTERVAL);
    """
    result = 0
    async with connection_pool.acquire() as conn:
        result = await conn.fetchval(query, test_provider["id"], lookback_window)

        if result >= infected_file_threshold:
            query = """
                UPDATE provider
                SET 
                    can_upload = false,
                    reason = $2
                WHERE id = $1 AND can_upload = true 
            """
            block_result = await conn.execute(query, test_provider["id"], "testing provider block email with files")
            if block_result == "UPDATE 1":
                blocked = True
    return blocked
