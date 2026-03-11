import pytest
import asyncpg
from datetime import datetime, timezone
import uuid

from app.v2.utils.api_keys import (create_api_key, list_api_keys, update_api_key,
                                   revoke_api_key,  record_api_key_usage, ApiKeyNotFoundError,
                                   ApiKeyPermissionError)
from app.v2.type_util.api_keys import ApiKeyCreateRequest, ApiKeyUpdateRequest
from app.v2.type_util.auth import AuthUser

@pytest.mark.asyncio
async def test_create_api_key(make_request, test_admin_user):
    """Test creating a personal api key."""
    req = make_request()
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", expires_in_days=10,
                                                      ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)

    assert api_key["id"]  
    assert api_key["name"] == mock_api_key_create_request.name 
    assert api_key["key"] 

@pytest.mark.asyncio
async def test_create_managed_user_api_key(make_request, test_ngroup_id, test_admin_user, seed_user):
    """Test creating a managed user api key."""
    req = make_request()
    mock_obs_user_id = uuid.uuid4()
    await seed_user(mock_obs_user_id, "test_email@test.com", "test_username_user", "test_user", '2068cc53-1232-4bc7-9647-3e29e6418e21')

    #key created by admin 
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="managed_user", target_user_id=mock_obs_user_id,
                                                      expires_in_days=10, ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)

    assert api_key["id"]
    assert api_key["name"] == mock_api_key_create_request.name 
    assert api_key["key"] 

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user",
                    "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')

    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    #key create by daac_manager
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_manager_for_observer_key", key_type="managed_user", target_user_id=mock_obs_user_id,
                                                      expires_in_days=10, ngroup_id=test_ngroup_id)
    api_key = await create_api_key(req, mock_api_key_create_request, mock_daac_manager)

    assert api_key["id"]
    assert api_key["name"] == mock_api_key_create_request.name 
    assert api_key["key"] 

@pytest.mark.asyncio
async def test_create_managed_user_api_key_target_user_does_not_exists(make_request, test_ngroup_id, seed_user):
    """Test path for creating managed user api key when user does not exists."""
    req = make_request()
    mock_obs_user_id = uuid.uuid4()

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user",
                    "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')

    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_manager_for_observer_key", key_type="managed_user", target_user_id=mock_obs_user_id,
                                                      expires_in_days=10, ngroup_id=test_ngroup_id)
    with pytest.raises(asyncpg.exceptions.ForeignKeyViolationError):
        await create_api_key(req, mock_api_key_create_request, mock_daac_manager)

@pytest.mark.asyncio
async def test_create_managed_user_api_key_manager_not_in_ngroup(make_request, test_ngroup_id, seed_ngroup, seed_user):
    """Test creating managed user api key as daac manager when target user is not in ngroup."""
    req = make_request()
    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")
    mock_obs_user_id = uuid.uuid4()
    await seed_user(mock_obs_user_id, "test_email@test.com", "test_username_user",
                    "test_user", '2068cc53-1232-4bc7-9647-3e29e6418e21', ngroup_id=ngroup_id2)

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user",
                    "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')

    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_manager_for_observer_key", key_type="managed_user", target_user_id=mock_obs_user_id,
                                                      expires_in_days=10, ngroup_id=ngroup_id2)
    with pytest.raises(ApiKeyPermissionError):
        await create_api_key(req, mock_api_key_create_request, mock_daac_manager)


@pytest.mark.asyncio
async def test_create_proxy_api_key(make_request, test_admin_user):
    """Test creating proxy api key"""
    req = make_request()
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="proxy", proxy_user_name="test_proxy_user",
                                                      expires_in_days=10, ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)

    assert api_key["id"]  
    assert api_key["name"] == mock_api_key_create_request.name 
    assert api_key["key"] 


@pytest.mark.asyncio
async def test_list_api_key(make_request, test_admin_user):
    """Test getting of list api keys"""
    req = make_request()
    mock_api_key_create_request1 = ApiKeyCreateRequest(name="test_key1", key_type="personal", expires_in_days=10,
                                                       ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    mock_api_key_create_request2 = ApiKeyCreateRequest(name="test_key2", key_type="proxy", expires_in_days=10,
                                                       proxy_user_name="test_proxy", ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    api_key1 = await create_api_key(req, mock_api_key_create_request1, test_admin_user)
    api_key2 = await create_api_key(req, mock_api_key_create_request2, test_admin_user)

    all_api_keys = await list_api_keys(req, test_admin_user, None)

    assert api_key1["id"] in [k.id for k in all_api_keys]
    assert api_key2["id"] in [k.id for k in all_api_keys]

@pytest.mark.asyncio
async def test_update_api_key(make_request, test_admin_user, connection_pool):
    """Test updating an api key as admin"""
    req = make_request()
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", expires_in_days=10, ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)
    api_key_id = api_key["id"]
    mock_api_key_update_request = ApiKeyUpdateRequest(is_active=False)
    await update_api_key(req, api_key_id, mock_api_key_update_request, test_admin_user)
    async with connection_pool.acquire() as conn:
        is_active = await conn.fetchval("SELECT is_active FROM api_key WHERE id = $1", api_key_id)
    assert not is_active

@pytest.mark.asyncio
async def test_update_api_key_personal(make_request, test_ngroup_id,seed_user, connection_pool):
    """Test updating a personal api as daac manager."""
    req = make_request()

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user", "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')
    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))

    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", expires_in_days=10, ngroup_id=test_ngroup_id)

    api_key = await create_api_key(req, mock_api_key_create_request, mock_daac_manager)
    api_key_id = api_key["id"]

    mock_api_key_update_request = ApiKeyUpdateRequest(is_active=False)
    await update_api_key(req, api_key_id, mock_api_key_update_request, mock_daac_manager)

    async with connection_pool.acquire() as conn:
        is_active = await conn.fetchval("SELECT is_active FROM api_key WHERE id = $1", api_key_id)
    assert not is_active

@pytest.mark.asyncio
async def test_update_api_key_as_manager_for_other(make_request, seed_user, test_ngroup_id, connection_pool):
    """Test updating another user's api key as daac manager."""
    req = make_request()

    mock_obs_user_id = uuid.uuid4()
    await seed_user(mock_obs_user_id, "test_email@test.com", "test_username_user", "test_user", '2068cc53-1232-4bc7-9647-3e29e6418e21')

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user",
                    "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')
    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))

    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="managed_user", target_user_id=mock_obs_user_id,
                                                      expires_in_days=10, ngroup_id=test_ngroup_id)

    api_key = await create_api_key(req, mock_api_key_create_request, mock_daac_manager)
    api_key_id = api_key["id"]

    mock_api_key_update_request = ApiKeyUpdateRequest(is_active=False)
    await update_api_key(req, api_key_id, mock_api_key_update_request, mock_daac_manager)

    async with connection_pool.acquire() as conn:
        is_active = await conn.fetchval("SELECT is_active FROM api_key WHERE id = $1", api_key_id)
    assert not is_active

@pytest.mark.asyncio
async def test_update_api_key_as_manager_for_other_no_permission(make_request, seed_ngroup, seed_user, test_ngroup_id):
    """Test updating a user's api key as daac manager, but user is in different ngroup."""
    req = make_request()

    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")

    mock_obs_user_id = uuid.uuid4()
    await seed_user(mock_obs_user_id, "test_email@test.com", "test_username_user",
                    "test_user", '2068cc53-1232-4bc7-9647-3e29e6418e21', ngroup_id=ngroup_id2)
    mock_daac_obs = AuthUser(id=mock_obs_user_id, email="test_daac_observer_email@test.com", 
                    cueusername="test_daac_observer_username_user", name="test daac observer",
                    roles=["daac_observer"], ngroups=[str(ngroup_id2)],
                    active_ngroup_id=str(ngroup_id2))

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user",
                    "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')
    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))

    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", expires_in_days=10, ngroup_id=ngroup_id2)

    api_key = await create_api_key(req, mock_api_key_create_request, mock_daac_obs)
    api_key_id = api_key["id"]

    mock_api_key_update_request = ApiKeyUpdateRequest(is_active=False)
    with pytest.raises(ApiKeyPermissionError):
        await update_api_key(req, api_key_id, mock_api_key_update_request, mock_daac_manager)


@pytest.mark.asyncio
async def test_revoke_api_key(make_request, test_admin_user, connection_pool):
    """Test revoking a user api key as admin."""
    req = make_request()
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", expires_in_days=10,
                                                      ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)
    api_key_id = api_key["id"]
    await revoke_api_key(req, api_key_id, test_admin_user) 
    async with connection_pool.acquire() as conn:
        result = await conn.fetchrow("SELECT is_active, revoked_at FROM api_key WHERE id = $1", api_key_id)
    assert not result["is_active"]
    assert result["revoked_at"]


@pytest.mark.asyncio
async def test_revoke_api_key_as_manager_for_other(make_request, seed_user, test_ngroup_id, connection_pool):
    """Test revoking another user's api key as daac manager."""
    req = make_request()

    mock_obs_user_id = uuid.uuid4()
    await seed_user(mock_obs_user_id, "test_email@test.com", "test_username_user", "test_user", '2068cc53-1232-4bc7-9647-3e29e6418e21')

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user",
                    "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')
    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))

    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="managed_user", target_user_id=mock_obs_user_id,
                                                      expires_in_days=10, ngroup_id=test_ngroup_id)

    api_key = await create_api_key(req, mock_api_key_create_request, mock_daac_manager)
    api_key_id = api_key["id"]

    await revoke_api_key(req, api_key_id, mock_daac_manager) 
    async with connection_pool.acquire() as conn:
        result = await conn.fetchrow("SELECT is_active, revoked_at FROM api_key WHERE id = $1", api_key_id)
    assert not result["is_active"]
    assert result["revoked_at"]

@pytest.mark.asyncio
async def test_revoke_api_key_as_manager_for_other_no_permission(make_request, seed_ngroup, seed_user, test_ngroup_id):
    """Test revoke another user's api key as daac manager but user is in different ngroup."""
    req = make_request()

    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")

    mock_obs_user_id = uuid.uuid4()
    await seed_user(mock_obs_user_id, "test_email@test.com", "test_username_user", "test_user", '2068cc53-1232-4bc7-9647-3e29e6418e21', ngroup_id=ngroup_id2)
    mock_daac_obs = AuthUser(id=mock_obs_user_id, email="test_daac_observer_email@test.com", 
                    cueusername="test_daac_observer_username_user", name="test daac observer",
                    roles=["daac_observer"], ngroups=[str(ngroup_id2)],
                    active_ngroup_id=str(ngroup_id2))

    mock_dm_user_id = uuid.uuid4()
    await seed_user(mock_dm_user_id, "test_daac_manager_email@test.com", "test_daac_manager_username_user", "test_daac_manager_user", 'ef872fe7-92b9-45ec-ac19-80f4c478fd36')
    mock_daac_manager = AuthUser(id=mock_dm_user_id, email="test_daac_manager_email@test.com", 
                    cueusername="test_daac_manager_username_user", name="test daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))

    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", expires_in_days=10, ngroup_id=ngroup_id2)

    api_key = await create_api_key(req, mock_api_key_create_request, mock_daac_obs)
    api_key_id = api_key["id"]

    with pytest.raises(ApiKeyPermissionError):
        await revoke_api_key(req, api_key_id, mock_daac_manager) 

@pytest.mark.asyncio
async def test_record_api_key_usage_key(make_request, test_admin_user, connection_pool):
    """Test recording api key usage"""
    req = make_request()
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", expires_in_days=10,
                                                      ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)
    api_key_id = api_key["id"]
    await record_api_key_usage(req, api_key_id)
    async with connection_pool.acquire() as conn:
        last_used_at = await conn.fetchval("SELECT last_used_at FROM api_key WHERE id = $1", api_key_id)
        now = datetime.now(tz=timezone.utc)
    assert abs((now - last_used_at).total_seconds()) <= 1 
    # Check last_used_at is update to a timestamp within the last second