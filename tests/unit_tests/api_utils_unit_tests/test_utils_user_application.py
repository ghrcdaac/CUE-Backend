import pytest
import pytest_asyncio
from typing import Tuple, Dict
from unittest.mock import patch, MagicMock
import uuid
import os

from app.v2.utils.user_application import (reject_application, approve_application, list_applications,
                                           get_application, submit_application, ApplicationNotFoundError, ApplicationInvalidStateError)
from app.v2.type_util.user_application import ApplicationStatus



@pytest.mark.asyncio
async def test_submit_application(make_request, make_user_application_create):
    """Test submitting a user application."""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    user_id = uuid.uuid4()

    new_app = await submit_application(req, mock_user_application, user_id)
    assert isinstance(new_app["id"], uuid.UUID)

@pytest.mark.asyncio
async def test_get_application (make_request, make_user_application_create):
    """Test getting a user application."""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    retrieved_app = await get_application(req, application_id)
    assert application_id == retrieved_app["id"]

@pytest.mark.asyncio
async def test_get_application_not_found (make_request):
    """Test getting a user application that does not exist."""
    req = make_request()
    application_id= uuid.uuid4()

    with pytest.raises(ApplicationNotFoundError):
        await get_application(req, application_id)

@pytest.mark.asyncio
async def test_list_applications(make_request, test_admin_user, test_ngroup_id, make_user_application_create):
    """Test getting a list of user_applications"""
    req = make_request()

    mock_user_application1 = make_user_application_create("test_user1@test.com", "test_user1", "test_username1", "test", "daac")
    mock_user_application2 = make_user_application_create("test_user2@test.com", "test_user2", "test_username2", "test", "provider")

    # for now
    user_id1 = uuid.uuid4()
    user_id2 = uuid.uuid4()

    app1 = await submit_application(req, mock_user_application1, user_id1)
    app2 = await submit_application(req, mock_user_application2, user_id2)

    all_apps = await list_applications(req, test_admin_user, str(test_ngroup_id))

    assert app1["id"] in [a["id"] for a in all_apps]
    assert app2["id"] in [a["id"] for a in all_apps]
    
@pytest.mark.asyncio
async def test_approve_application(make_request, connection_pool, make_user_application_create, test_admin_user):
    """Test approving a user application as admin"""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    # DAAC staff
    role_id = "a8b3757b-dcf9-4943-8f64-5adaf17a17fe"

    profile = await approve_application(req, application_id, role_id, test_admin_user)
    assert isinstance(profile,dict)

    #Check DB
    async with connection_pool.acquire() as conn:
        user_app_approved = await conn.fetchrow("SELECT * FROM user_application WHERE user_id = $1", user_id)
    assert user_app_approved["status"] == "approved"
    assert profile["roles"][0] == "daac_staff"

@pytest.mark.asyncio
async def test_approve_application_daac_manager_approve(make_request, connection_pool, make_user_application_create, test_daac_manager_user):
    """Test approve user application as daac manager."""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    # for now
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    # DAAC staff 
    role_id = "a8b3757b-dcf9-4943-8f64-5adaf17a17fe" 

    profile = await approve_application(req, application_id, role_id, test_daac_manager_user)
    assert isinstance(profile,dict)

    #Check DB
    async with connection_pool.acquire() as conn:
        user_app_approved = await conn.fetchrow("SELECT * FROM user_application WHERE user_id = $1", user_id)
    assert user_app_approved["status"] == "approved"
    assert profile["roles"][0] == "daac_staff"

@pytest.mark.asyncio
async def test_approve_application_daac_manager_approve_admin_role(make_request, make_user_application_create, test_daac_manager_user):
    """Test approving user application as daac manager, but trying to assign new user admin role"""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    # for now
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    # Admin 
    role_id = "c924d0d3-55af-49f3-bec1-d7fd4ed475e2"

    with pytest.raises(ValueError):
        await approve_application(req, application_id, role_id, test_daac_manager_user)

@pytest.mark.asyncio
async def test_approve_application_security_approve(make_request, connection_pool, make_user_application_create, test_security_user):
    """Test approving user application as security, new security user."""
    req = make_request()
    #Consider changing security_user ngroup 

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    # for now
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    # Security 
    role_id = "39677929-ba9b-426d-8c18-f607d669fcce" 

    profile = await approve_application(req, application_id, role_id, test_security_user)
    assert isinstance(profile,dict)

    #Check DB
    async with connection_pool.acquire() as conn:
        user_app_approved = await conn.fetchrow("SELECT * FROM user_application WHERE user_id = $1", user_id)
    assert user_app_approved["status"] == "approved"
    assert profile["roles"][0] == "security"

@pytest.mark.asyncio
async def test_approve_application_security_approve_admin_role(make_request, make_user_application_create, test_security_user):
    """Test approving user application as security user, new admin user."""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    # for now
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    # Admin 
    role_id = "c924d0d3-55af-49f3-bec1-d7fd4ed475e2"

    with pytest.raises(ValueError):
        await approve_application(req, application_id, role_id, test_security_user)

@pytest.mark.asyncio
async def test_approve_application_non_valid_approver_approve_fail(make_request, make_user_application_create, test_daac_staff_user):
    """Test approving user application as daac staff."""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    # for now
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    # Admin 
    role_id = "c924d0d3-55af-49f3-bec1-d7fd4ed475e2"

    with pytest.raises(ValueError):
        await approve_application(req, application_id, role_id, test_daac_staff_user)

@pytest.mark.asyncio
async def test_approve_application_role_does_not_exist(make_request, make_user_application_create, test_admin_user):
    """Test approving user application but role does not exist"""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    # for now
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    # bad role 
    role_id = str(uuid.uuid4())

    with pytest.raises(ValueError):
        await approve_application(req, application_id, role_id, test_admin_user)

@pytest.mark.asyncio
async def test_approve_application_application_does_not_exist(make_request, test_admin_user):
    """Test approving user application, but application does not exist."""
    req = make_request()

    application_id = uuid.uuid4()

    # Admin 
    role_id = "c924d0d3-55af-49f3-bec1-d7fd4ed475e2"

    with pytest.raises(ApplicationNotFoundError):
        await approve_application(req, application_id, role_id, test_admin_user)

@pytest.mark.asyncio
async def test_reject_application (make_request, make_user_application_create):
    """Test rejecting user application."""
    req = make_request()

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    application_id = app["id"]

    rejected_app = await reject_application(req, application_id)
    assert application_id == rejected_app["id"]
    assert app["status"] != rejected_app["status"] 
    assert rejected_app["status"] == ApplicationStatus.REJECTED

@pytest.mark.asyncio
async def test_reject_application_as_spam_hides_from_list(make_request, make_user_application_create, test_admin_user, test_ngroup_id):
    """Test rejecting an application as spam hides it from dashboard listings."""
    req = make_request()

    mock_user_application = make_user_application_create("spam_user@test.com", "spam_user", "spam_username", "test", "daac")
    user_id = uuid.uuid4()

    app = await submit_application(req, mock_user_application, user_id)
    rejected_app = await reject_application(req, app["id"], mark_as_spam=True)
    all_apps = await list_applications(req, test_admin_user, str(test_ngroup_id))

    assert rejected_app["status"] == ApplicationStatus.REJECTED
    assert rejected_app["is_spam"] is True
    assert app["id"] not in [a["id"] for a in all_apps]

@pytest.mark.asyncio
async def test_spam_email_cannot_submit_future_application(make_request, make_user_application_create):
    """Test an email marked as spam cannot submit another application."""
    req = make_request()

    spam_application = make_user_application_create("blocked_user@test.com", "blocked_user", "blocked_username", "test", "daac")
    app = await submit_application(req, spam_application, uuid.uuid4())
    await reject_application(req, app["id"], mark_as_spam=True)

    future_application = make_user_application_create("Blocked_User@Test.com", "blocked_user2", "blocked_username2", "test", "daac")
    with pytest.raises(ValueError, match="spam"):
        await submit_application(req, future_application, uuid.uuid4())
