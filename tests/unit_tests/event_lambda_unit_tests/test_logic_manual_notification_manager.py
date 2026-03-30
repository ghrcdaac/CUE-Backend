import pytest
import uuid
from botocore.exceptions import ClientError
from app.event_lambdas.manual_notification_manager.logic import validate_notification, invoke_notification_manager, ManualNotificationError
from app.event_lambdas.manual_notification_manager.model import Notification

@pytest.mark.asyncio
async def test_validate_notification_user_app_submitted(connection_pool, test_ngroup_id, test_provider):
    """Test validating a valid user application submitted notification."""
    insert_query = """
        INSERT INTO user_application (email, name, username, status, ngroup_id, provider_id, justification, account_type)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, email, name, username, status, ngroup_id, provider_id, justification, account_type
    """
    async with connection_pool.acquire() as conn:
        result = await conn.fetchrow(insert_query, *("test_email@test.com", "test user", "test_user", "pending", str(test_ngroup_id), test_provider["id"], "test", "daac"))
    app_id = str(result["id"])
    notification = {"detail-type":"UserApplicationSubmitted", "detail":{"application_id":app_id}, "user_id":uuid.uuid4() }
    parsed_notification = await validate_notification(connection_pool, notification)
    assert isinstance(parsed_notification, Notification)

@pytest.mark.asyncio
async def test_validate_notification_user_app_submitted_fail(connection_pool):
    """Test validating a invalid user application submitted notification """
    notification = {"detail-type":"UserApplicationSubmitted", "detail":{}, "user_id":uuid.uuid4()}

    with pytest.raises(ManualNotificationError):
        await validate_notification(connection_pool, notification)

@pytest.mark.asyncio
async def test_validate_notification_user_app_approved(connection_pool, test_ngroup_id, test_provider):
    """Test validating a valid user application approved user notification"""
    insert_query = """
        INSERT INTO user_application (email, name, username, status, ngroup_id, provider_id, justification, account_type, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, email, name, username, status, ngroup_id, provider_id, justification, account_type
    """
    user_id = str(uuid.uuid4())
    async with connection_pool.acquire() as conn:
        await conn.execute(insert_query, *("test_email@test.com", "test user", "test_user", "approved", str(test_ngroup_id), test_provider["id"], "test", "daac", user_id))

    notification = {"detail-type":"UserApplicationApproved", "detail":{"user_id":user_id}, "user_id":uuid.uuid4() }
    await validate_notification(connection_pool, notification)

@pytest.mark.asyncio
async def test_validate_notification_user_app_approved_fail(connection_pool):
    """Test validating a invalid user application approved notification."""
    user_id = str(uuid.uuid4())
    notification = {"detail-type":"UserApplicationApproved", "detail":{"user_id":user_id}, "user_id": uuid.uuid4()}
    with pytest.raises(ManualNotificationError):
        await validate_notification(connection_pool, notification)

@pytest.mark.asyncio
async def test_validate_notification_infected_file(connection_pool, seed_file, test_admin_user):
    """Test validating valid infected file notification."""
    file_id = str(uuid.uuid4())
    await seed_file(file_id, "file", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    notification = {"detail-type":"InfectedFileFound", "detail":{"key":file_id}, "user_id":str(uuid.uuid4())}
    await validate_notification(connection_pool, notification)

@pytest.mark.asyncio
async def test_validate_notification_infected_file_fail(connection_pool):
    """Test validation invalid infected file notification."""
    notification = {"detail-type":"InfectedFileFound", "detail":{"key":str(uuid.uuid4()), "user_id":str(uuid.uuid4())}}
    with pytest.raises(ManualNotificationError):
        await validate_notification(connection_pool, notification)

@pytest.mark.asyncio
async def test_validate_notification_fail(connection_pool):
    """Test validating empty notification"""
    notification = {}
    with pytest.raises(ManualNotificationError):
        await validate_notification(connection_pool, notification)

@pytest.mark.asyncio
async def test_invoke_notification_manager(mock_boto3_client):
    """Test invoking notification manager lambda"""
    await invoke_notification_manager("UserApplicationApproved",{"user_id":str(uuid.uuid4())})

@pytest.mark.asyncio
async def test_invoke_notification_manager_fail(mock_boto3_client):
    """Test invoking notification manager lambda, but lambda client fails to invoke lambda"""
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")

    with pytest.raises(ManualNotificationError):
        await invoke_notification_manager("UserApplicationApproved", {"user_id":uuid.uuid4()})