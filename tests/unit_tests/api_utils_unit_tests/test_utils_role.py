import pytest
import uuid

from app.v2.utils.role import (create_role, get_role, get_role_by_lookup,
                               list_roles, update_role, delete_role, RoleNotFoundError)
from app.v2.type_util.role import RoleCreate, RoleUpdate

@pytest.mark.asyncio
async def test_create_role(make_request, connection_pool):
    """Test creating a role."""
    req = make_request()
    req.state.pool = connection_pool

    mock_role_create = RoleCreate(short_name="mock_role", long_name="mock role")
    new_role = await create_role(req, mock_role_create)
    assert isinstance(new_role["id"],uuid.UUID)

@pytest.mark.asyncio
async def test_get_role(make_request, connection_pool):
    """Test getting a role."""
    req = make_request()
    req.state.pool = connection_pool

    mock_role_create = RoleCreate(short_name="mock_role", long_name="mock role")
    role = await create_role(req, mock_role_create)
    role_id = role["id"]

    retrieved_role = await get_role(req, role_id)
    assert role_id == retrieved_role["id"]
    assert role["short_name"] == retrieved_role["short_name"]
    assert role["long_name"] == retrieved_role["long_name"]

@pytest.mark.asyncio
async def test_get_role_not_found(make_request, connection_pool):
    """Test getting a role that doest not exist."""
    req = make_request()
    req.state.pool = connection_pool

    role_id = uuid.uuid4()
     
    with pytest.raises(RoleNotFoundError):
        await get_role(req, role_id)


@pytest.mark.asyncio
async def test_get_role_by_lookup(make_request, connection_pool):
    """Test getting a role by looking it up by its short name and/or long name"""
    req = make_request()
    req.state.pool = connection_pool

    mock_role_create = RoleCreate(short_name="mock_role", long_name="mock role")
    role = await create_role(req, mock_role_create)
    role_short_name = role["short_name"]
    role_long_name = role["long_name"]

    retrieved_role_short = await get_role_by_lookup(req, role_short_name, None)
    assert role["id"] == retrieved_role_short["id"]
    assert role["short_name"] == retrieved_role_short["short_name"]
    assert role["long_name"] == retrieved_role_short["long_name"]

    retrieved_role_long = await get_role_by_lookup(req, None, role_long_name)
    assert role["id"] == retrieved_role_long["id"]
    assert role["short_name"] == retrieved_role_long["short_name"]
    assert role["long_name"] == retrieved_role_long["long_name"]

    retrieved_role = await get_role_by_lookup(req, role_short_name, role_long_name)
    assert role["id"] == retrieved_role["id"]
    assert role["short_name"] == retrieved_role["short_name"]
    assert role["long_name"] == retrieved_role["long_name"]

@pytest.mark.asyncio
async def test_get_role_by_lookup_not_found(make_request, connection_pool):
    """Test getting a role by looking up is names, but role does not exist."""
    req = make_request()
    req.state.pool = connection_pool

    role_short_name = "short"
    role_long_name = "long"
     
    with pytest.raises(RoleNotFoundError):
        await get_role_by_lookup(req, role_short_name, None)

    with pytest.raises(RoleNotFoundError):
        await get_role_by_lookup(req, None, role_long_name)

    with pytest.raises(RoleNotFoundError):
        await get_role_by_lookup(req, role_short_name, role_long_name)

@pytest.mark.asyncio
async def test_list_roles(make_request, connection_pool):
    """Test getting a list of roles."""
    req = make_request()
    req.state.pool = connection_pool

    mock_role_create1 = RoleCreate(short_name="mock_role", long_name="mock role")
    mock_role_create2 = RoleCreate(short_name="short", long_name="long")
    role1 = await create_role(req, mock_role_create1)
    role2 = await create_role(req, mock_role_create2)

    all_roles = await list_roles(req)

    assert role1["id"] in [r["id"] for r in all_roles]
    assert role2["id"] in [r["id"] for r in all_roles]


@pytest.mark.asyncio
async def test_update_role(make_request, connection_pool):
    """Test updating a role."""
    req = make_request()
    req.state.pool = connection_pool

    mock_role_create = RoleCreate(short_name="mock_role", long_name="mock role")
    role = await create_role(req, mock_role_create)
    role_id = role["id"]

    mock_role_update = RoleUpdate(short_name="new_short_name", long_name="new_long_name")
    updated_role = await update_role(req, role_id, mock_role_update)

    retrieved_role = await get_role(req, role_id)
    assert role_id == retrieved_role["id"] and role_id == updated_role["id"]
    assert retrieved_role["short_name"] == updated_role["short_name"] 
    assert retrieved_role["long_name"] == updated_role["long_name"] 

@pytest.mark.asyncio
async def test_update_role_not_found(make_request, connection_pool):
    """Testing updating a role, but the role does not exist."""
    req = make_request()
    req.state.pool = connection_pool

    role_id = uuid.uuid4()
    mock_role_update = RoleUpdate(short_name="new_short_name", long_name="new_long_name")
     
    with pytest.raises(RoleNotFoundError):
        await update_role(req, role_id, mock_role_update)

@pytest.mark.asyncio
async def test_delete_role(make_request, connection_pool):
    """Test deleting a role."""
    req = make_request()
    req.state.pool = connection_pool

    mock_role_create = RoleCreate(short_name="mock_role", long_name="mock role")
    role = await create_role(req, mock_role_create)
    role_id = role["id"]

    await delete_role(req, role_id)

    async with connection_pool.acquire() as conn:
       db_role_id = await conn.fetchval("SELECT from role WHERE id = $1", role_id)

    assert db_role_id is None

@pytest.mark.asyncio
async def test_delete_role_not_found(make_request, connection_pool):
    """Test deleting a role."""
    req = make_request()
    req.state.pool = connection_pool

    with pytest.raises(RoleNotFoundError):
        await delete_role(req, uuid.uuid4())
