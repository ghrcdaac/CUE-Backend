import pytest
import uuid

from app.v2.utils.cueuser import (create_new_user, get_user_profile, list_users,
                                  get_user_profile_by_username, find_users_by_criteria, get_users_by_role,
                                  delete_user_fully, update_user_details, update_user_role, UserNotFoundError)
from app.v2.type_util.cueuser import UserUpdateRequest

@pytest.mark.asyncio
async def test_get_user_profile(make_request, test_admin_user):
    """Test getting a user profile"""
    req = make_request()
    user_id = test_admin_user.id
    profile = await get_user_profile(req, user_id)
    assert profile["id"] == user_id
    assert profile["roles"][0] == "admin"
    assert profile["ngroups"][0]["id"] == str(test_admin_user.ngroups[0])

@pytest.mark.asyncio
async def test_get_user_profile_user_does_not_exist(make_request):
    """Testing getting a user profile for user that does not exist."""
    req = make_request()
    user_id = uuid.uuid4()
    with pytest.raises(UserNotFoundError):
        await get_user_profile(req, user_id)

@pytest.mark.asyncio
async def test_create_new_user(make_request, test_ngroup_id, test_provider):
    """Test creating new user."""
    req = make_request()
    user_id = uuid.uuid4()
    email = "test_user@test.com" 
    name = "test_user"
    cueusername = "test_username"
    role_id = "a8b3757b-dcf9-4943-8f64-5adaf17a17fe" # DAAC Staff
    edpub_id = None

    profile = await create_new_user(req, user_id, email,
                                    name, cueusername, role_id,
                                    edpub_id, [test_ngroup_id], [test_provider["id"]])
    assert profile["id"] == user_id
    assert profile["roles"][0] == "daac_staff"
    assert profile["ngroups"][0]["id"] == str(test_ngroup_id)

@pytest.mark.asyncio
async def test_create_new_user_user_already_exists(make_request, test_ngroup_id, test_provider):
    """Test creating new user but user already exists."""
    req = make_request()
    user_id = uuid.uuid4()
    email = "test_user@test.com" 
    name = "test_user"
    cueusername = "test_username"
    role_id = "a8b3757b-dcf9-4943-8f64-5adaf17a17fe" # DAAC Staff
    edpub_id = None

    await create_new_user(req, user_id, email, name, cueusername, role_id, edpub_id, [test_ngroup_id], [test_provider["id"]])
    with pytest.raises(ValueError):
        await create_new_user(req, user_id, email, name, cueusername, role_id, edpub_id, [test_ngroup_id], [test_provider["id"]])

@pytest.mark.asyncio
async def test_create_new_user_no_ngroup_id_and_provider_id(make_request):
    """Test creating new user, but no ngroup_id or provider_id provided."""
    req = make_request()
    user_id = uuid.uuid4()
    email = "test_user@test.com" 
    name = "test_user"
    cueusername = "test_username"
    role_id = "a8b3757b-dcf9-4943-8f64-5adaf17a17fe" # DAAC Staff
    edpub_id = None

    with pytest.raises(ValueError):
        await create_new_user(req, user_id, email, name, cueusername, role_id, edpub_id, [], [])

@pytest.mark.asyncio
async def test_list_users(make_request, test_admin_user, make_cueuser):
    """Test getting a list of users."""
    req = make_request()
    active_ngroup_id = test_admin_user.ngroups[0] # None
    user1 = make_cueuser(uuid.uuid4(), "test_user1@test.com", "test_user1", "test_username1", provider_ids=None)
    user2 = make_cueuser(uuid.uuid4(), "test_user2@test.com", "test_user2", "test_username2", provider_ids=None)

    profile1 = await create_new_user(req, user1["user_id"], user1["email"],
                                     user1["name"], user1["cueusername"], user1["role_id"],
                                     user1["edpub_id"], user1["ngroup_ids"], user1["provider_ids"])
    profile2 = await create_new_user(req, user2["user_id"], user2["email"],
                                     user2["name"], user2["cueusername"], user2["role_id"],
                                     user2["edpub_id"], user2["ngroup_ids"], user2["provider_ids"])

    all_users = await list_users(req, test_admin_user, active_ngroup_id)
    assert profile1["id"] in [u["id"] for u in all_users] 
    assert profile2["id"] in [u["id"] for u in all_users] 

@pytest.mark.asyncio
async def test_get_user_profile_by_username(make_request, test_admin_user):
    """Test getting a user's profile by their username."""
    req = make_request()

    profile = await get_user_profile_by_username(req, test_admin_user.cueusername)
    assert profile["id"] == test_admin_user.id
    assert profile["cueusername"] == test_admin_user.cueusername

@pytest.mark.asyncio
async def test_get_user_profile_by_username_username_does_not_exist(make_request):
    """Test getting user's profile by their username, but the user name does not exist."""
    req = make_request()
    with pytest.raises(UserNotFoundError):
        await get_user_profile_by_username(req, "not_a_user_name")

@pytest.mark.asyncio
async def test_find_users_by_criteria(make_request, test_admin_user, make_cueuser):
    """Test find a user by criteria - username, email, name, edpub_id"""
    req = make_request()
    # username
    profile = await find_users_by_criteria(req, None, test_admin_user.cueusername, None, None)
    assert profile[0]["id"] == test_admin_user.id
    assert profile[0]["cueusername"] == test_admin_user.cueusername

    # email
    profile = await find_users_by_criteria(req, test_admin_user.email, None, None, None)
    assert profile[0]["id"] == test_admin_user.id
    assert profile[0]["email"] == test_admin_user.email

    # name
    profile = await find_users_by_criteria(req, None, None, test_admin_user.name, None)
    assert profile[0]["id"] == test_admin_user.id
    assert profile[0]["name"] == test_admin_user.name

    # edpub_id
    user = make_cueuser(uuid.uuid4(), "test_user1@test.com", "test_user1",
                        "test_username1", role_id="0e686dba-e5b2-4302-aea0-e9ed0caff7d3", edpub_id=str(uuid.uuid4()))
    await create_new_user(req, user["user_id"], user["email"],
                          user["name"], user["cueusername"], user["role_id"],
                          user["edpub_id"], user["ngroup_ids"], user["provider_ids"]) 
    profile = await find_users_by_criteria(req, None, None, None, user["edpub_id"])
    assert profile[0]["id"] == user["user_id"]
    assert profile[0]["edpub_id"] == user["edpub_id"]

@pytest.mark.asyncio
async def test_find_users_by_criteria_no_criteria(make_request, test_admin_user, make_cueuser):
    """Test finding user by criteria but no criteria provided."""
    req = make_request()

    with pytest.raises(ValueError):
        await find_users_by_criteria(req, None, None, None, None)

@pytest.mark.asyncio
async def test_get_user_by_role(make_request, make_cueuser):
    """Test getting user by role_id."""
    # 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2' - 'admin'
    # '39677929-ba9b-426d-8c18-f607d669fcce' - 'security'
    # 'ef872fe7-92b9-45ec-ac19-80f4c478fd36' - 'daac_manager'
    # 'a8b3757b-dcf9-4943-8f64-5adaf17a17fe' - 'daac_staff'
    # '2068cc53-1232-4bc7-9647-3e29e6418e21' - 'daac_observer'
    # '0e686dba-e5b2-4302-aea0-e9ed0caff7d3' - 'provider'
    req = make_request()
    admin_user = make_cueuser(uuid.uuid4(), "test_admin@test.com", "test_admin",
                              "test_admin_user_role_test", role_id="c924d0d3-55af-49f3-bec1-d7fd4ed475e2", edpub_id=None)
    await create_new_user(req, admin_user["user_id"], admin_user["email"],
                          admin_user["name"], admin_user["cueusername"], admin_user["role_id"],
                          admin_user["edpub_id"], admin_user["ngroup_ids"], admin_user["provider_ids"]) 

    security_user = make_cueuser(uuid.uuid4(), "test_security@test.com", "test_security",
                                 "test_security_user_role_test", role_id="39677929-ba9b-426d-8c18-f607d669fcce", edpub_id=None)
    await create_new_user(req, security_user["user_id"], security_user["email"],
                          security_user["name"], security_user["cueusername"], security_user["role_id"],
                          security_user["edpub_id"], security_user["ngroup_ids"], security_user["provider_ids"]) 

    manager_user = make_cueuser(uuid.uuid4(), "test_manager@test.com", "test_manager",
                                "test_manager_user_role_test", role_id="ef872fe7-92b9-45ec-ac19-80f4c478fd36", edpub_id=None)
    await create_new_user(req, manager_user["user_id"], manager_user["email"],
                          manager_user["name"], manager_user["cueusername"], manager_user["role_id"],
                          manager_user["edpub_id"], manager_user["ngroup_ids"], manager_user["provider_ids"]) 

    staff_user1 = make_cueuser(uuid.uuid4(), "test_staff1@test.com", "test_staff1",
                               "test_staff_user1", role_id="a8b3757b-dcf9-4943-8f64-5adaf17a17fe", edpub_id=None)
    await create_new_user(req, staff_user1["user_id"], staff_user1["email"],
                          staff_user1["name"], staff_user1["cueusername"], staff_user1["role_id"],
                          staff_user1["edpub_id"], staff_user1["ngroup_ids"], staff_user1["provider_ids"]) 

    staff_user2 = make_cueuser(uuid.uuid4(), "test_staff2@test.com", "test_staff2",
                               "test_staff_user2", role_id="a8b3757b-dcf9-4943-8f64-5adaf17a17fe", edpub_id=None)
    await create_new_user(req, staff_user2["user_id"], staff_user2["email"],
                          staff_user2["name"], staff_user2["cueusername"], staff_user2["role_id"],
                          staff_user2["edpub_id"], staff_user2["ngroup_ids"], staff_user2["provider_ids"]) 

    observer_user = make_cueuser(uuid.uuid4(), "test_observer@test.com", "test_observer",
                                 "test_observer_user_role_test", role_id="a8b3757b-dcf9-4943-8f64-5adaf17a17fe", edpub_id=None)
    await create_new_user(req, observer_user["user_id"], observer_user["email"],
                          observer_user["name"], observer_user["cueusername"], observer_user["role_id"],
                          observer_user["edpub_id"], observer_user["ngroup_ids"], observer_user["provider_ids"]) 

    provider_user = make_cueuser(uuid.uuid4(), "test_provider@test.com", "test_provider",
                                 "test_provider_user_role_test", role_id="0e686dba-e5b2-4302-aea0-e9ed0caff7d3", edpub_id=str(uuid.uuid4()))
    await create_new_user(req, provider_user["user_id"], provider_user["email"],
                          provider_user["name"], provider_user["cueusername"], provider_user["role_id"],
                          provider_user["edpub_id"], provider_user["ngroup_ids"], provider_user["provider_ids"]) 

    role_id = "a8b3757b-dcf9-4943-8f64-5adaf17a17fe"
    users = await get_users_by_role(req, role_id)

    assert staff_user1["user_id"] in [u["id"] for u in users]
    assert staff_user2["user_id"] in [u["id"] for u in users]

@pytest.mark.asyncio
async def test_delete_user_fully(make_request, make_cueuser, connection_pool):
    """Test deleting user fully."""
    req = make_request()
    admin_user = make_cueuser(uuid.uuid4(), "test_admin@test.com", "test_admin_user",
                               "test_admin", role_id="c924d0d3-55af-49f3-bec1-d7fd4ed475e2", edpub_id=None)
    await create_new_user(req, admin_user["user_id"], admin_user["email"],
                          admin_user["name"], admin_user["cueusername"], admin_user["role_id"],
                          admin_user["edpub_id"], admin_user["ngroup_ids"], admin_user["provider_ids"])

    await delete_user_fully(req, admin_user["user_id"])
    async with connection_pool.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM cueuser WHERE id = $1", admin_user["user_id"])
    assert user_id is None

@pytest.mark.asyncio
async def test_update_user_details(make_request, make_cueuser):
    """Test updating a user details."""
    req = make_request()
    admin_user = make_cueuser(uuid.uuid4(), "test_admin@test.com", "test_admin_user",
                              "test_admin", role_id="c924d0d3-55af-49f3-bec1-d7fd4ed475e2", edpub_id=None)
    await create_new_user(req, admin_user["user_id"], admin_user["email"], admin_user["name"],
                          admin_user["cueusername"], admin_user["role_id"], admin_user["edpub_id"],
                          admin_user["ngroup_ids"], admin_user["provider_ids"]) 

    mock_user_update_request = UserUpdateRequest(name="new_admin_name", email="new_admin_email@test.com", edpub_id=str(uuid.uuid4()))
    updated_user = await update_user_details(req, admin_user["user_id"], mock_user_update_request)

    assert updated_user["name"] == mock_user_update_request.name
    assert updated_user["email"] == mock_user_update_request.email
    assert updated_user["edpub_id"] == mock_user_update_request.edpub_id

@pytest.mark.asyncio
async def test_update_user_role_as_admin(make_request, make_cueuser, test_admin_user):
    """Test updating a user role as a admin."""
    req = make_request()

    user = make_cueuser(uuid.uuid4(), "test_user@test.com", "test",
                        "test_user", role_id="2068cc53-1232-4bc7-9647-3e29e6418e21", edpub_id=None)
    await create_new_user(req, user["user_id"], user["email"],
                          user["name"], user["cueusername"], user["role_id"],
                          user["edpub_id"], user["ngroup_ids"], user["provider_ids"]) 

    # update user.role from daac_observer to daac manager
    updated_user = await update_user_role(req, user["user_id"], "ef872fe7-92b9-45ec-ac19-80f4c478fd36", test_admin_user)
    assert updated_user["roles"][0] == 'daac_manager'

@pytest.mark.asyncio
async def test_update_user_role_as_daac_manager(make_request, make_cueuser, test_daac_manager_user):
    """Test updating a user role a daac manager, update role daac manager"""
    req = make_request()

    user = make_cueuser(uuid.uuid4(), "test_user@test.com", "test",
                        "test_user", role_id="2068cc53-1232-4bc7-9647-3e29e6418e21", edpub_id=None)
    await create_new_user(req, user["user_id"], user["email"],
                          user["name"], user["cueusername"], user["role_id"],
                          user["edpub_id"], user["ngroup_ids"], user["provider_ids"]) 

    # update user.role from daac_observer to daac manager
    updated_user = await update_user_role(req, user["user_id"], "ef872fe7-92b9-45ec-ac19-80f4c478fd36", test_daac_manager_user)
    assert updated_user["roles"][0] == 'daac_manager'

@pytest.mark.asyncio
async def test_update_user_role_as_daac_manager_non_allowed_role(make_request, make_cueuser, test_daac_manager_user):
    """Test updating a user's role as daac manager, update role - security."""
    req = make_request()

    user = make_cueuser(uuid.uuid4(), "test_user@test.com", "test",
                        "test_user", role_id="2068cc53-1232-4bc7-9647-3e29e6418e21", edpub_id=None)
    await create_new_user(req, user["user_id"], user["email"],
                          user["name"], user["cueusername"], user["role_id"],
                          user["edpub_id"], user["ngroup_ids"], user["provider_ids"])

    # update user.role from daac_observer to security
    with pytest.raises(ValueError):
        await update_user_role(req, user["user_id"],  "39677929-ba9b-426d-8c18-f607d669fcce", test_daac_manager_user)

@pytest.mark.asyncio
async def test_update_user_role_as_security(make_request, make_cueuser, test_security_user):
    """Test updating user's role as security, update role - security."""
    req = make_request()

    user = make_cueuser(uuid.uuid4(), "test_user@test.com", "test",
                        "test_user", role_id="2068cc53-1232-4bc7-9647-3e29e6418e21", edpub_id=None)
    await create_new_user(req, user["user_id"], user["email"],
                          user["name"], user["cueusername"], user["role_id"],
                          user["edpub_id"], user["ngroup_ids"], user["provider_ids"]) 

    # update user.role from daac_observer to security
    updated_user = await update_user_role(req, user["user_id"], "39677929-ba9b-426d-8c18-f607d669fcce", test_security_user)
    assert updated_user["roles"][0] == 'security'

@pytest.mark.asyncio
async def test_update_user_role_as_security_non_allowed_role(make_request, make_cueuser, test_security_user):
    """Test updating a user's role as security, update role - provider."""
    req = make_request()

    user = make_cueuser(uuid.uuid4(), "test_user@test.com", "test", "test_user", role_id="2068cc53-1232-4bc7-9647-3e29e6418e21", edpub_id=None)
    await create_new_user(req, user["user_id"], user["email"], user["name"], user["cueusername"], user["role_id"], user["edpub_id"], user["ngroup_ids"], user["provider_ids"]) 

    # update user.role from daac_observer to provider
    with pytest.raises(ValueError):
        await update_user_role(req, user["user_id"], "0e686dba-e5b2-4302-aea0-e9ed0caff7d3", test_security_user)