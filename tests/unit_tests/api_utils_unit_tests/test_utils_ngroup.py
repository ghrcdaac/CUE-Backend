import pytest
import pytest_asyncio
from typing import Tuple, Dict
from unittest.mock import patch, MagicMock
import uuid
import os

from app.v2.utils.ngroup import (create_ngroup, get_ngroup, update_ngroup,
                                 delete_ngroup, list_ngroups, list_ngroups_for_form, NgroupNotFoundError)
from app.v2.type_util.ngroup import NgroupCreate, NgroupUpdate

@pytest.mark.asyncio
async def test_create_ngroup(make_request):
    """Test creating a ngroup."""
    req = make_request()

    mock_ngroup_create = NgroupCreate(short_name="test_ngroup", long_name="Test Ngroup")

    result = await create_ngroup(req, mock_ngroup_create)
    assert isinstance(result, Dict)
    assert result["short_name"] == mock_ngroup_create.short_name
    assert result["long_name"] == mock_ngroup_create.long_name

@pytest.mark.asyncio
async def test_get_ngroup(make_request, connection_pool):
    """Test getting a ngroup"""
    # First, create an ngroup record
    req = make_request()

    mock_ngroup_create = NgroupCreate(short_name="test_ngroup", long_name="Test Ngroup")

    created_ngroup = await create_ngroup(req, mock_ngroup_create)

    get_req = make_request()
    get_req.state.pool = connection_pool
    ## Then, try to get it
    retrieved_ngroup = await get_ngroup(get_req, created_ngroup["id"])
    assert retrieved_ngroup["id"] == created_ngroup["id"]
    assert retrieved_ngroup["short_name"] == created_ngroup["short_name"]
    assert retrieved_ngroup["long_name"] == created_ngroup["long_name"]

@pytest.mark.asyncio
async def test_get_ngroup_not_found(make_request, connection_pool):
    """Test getting a ngroup that does not exist."""
    # Try to get a non-existent ngroup
    get_req = make_request()
    get_req.state.pool = connection_pool

    with pytest.raises(NgroupNotFoundError):
       await get_ngroup(get_req, uuid.uuid4())

@pytest.mark.asyncio
async def test_update_ngroup(make_request):
    """Test updating a ngroup."""
    # Create an ngroup record
    req = make_request()

    mock_ngroup_create = NgroupCreate(short_name="test_ngroup", long_name="Test Ngroup")

    created_ngroup = await create_ngroup(req, mock_ngroup_create)

    # Update the ngroup record
    req = make_request()

    mock_ngroup_update = NgroupUpdate(short_name="updated_group", long_name="Updated Group")

    updated_ngroup = await update_ngroup(req, created_ngroup["id"], mock_ngroup_update)

    # Check if the record was updated
    assert updated_ngroup["id"] == created_ngroup["id"]
    assert updated_ngroup["short_name"] == mock_ngroup_update.short_name
    assert updated_ngroup["long_name"] == mock_ngroup_update.long_name

@pytest.mark.asyncio
async def test_update_ngroup_empty_update(make_request):
    """Test updating a ngroup without a empty update"""
    # Create an ngroup record
    req = make_request()

    mock_ngroup_create = NgroupCreate(short_name="test_ngroup", long_name="Test Ngroup")

    created_ngroup = await create_ngroup(req, mock_ngroup_create)

    # Update the ngroup record
    req = make_request()

    mock_ngroup_update = NgroupUpdate()
    with pytest.raises(ValueError):
        await update_ngroup(req, created_ngroup["id"], mock_ngroup_update)


@pytest.mark.asyncio
async def test_update_ngroup_not_found(make_request):
    """Test updating an ngroup that does not exist"""
    req = make_request()

    mock_ngroup_update = NgroupUpdate(short_name="updated_group", long_name="Updated Group")

    # Try to update a non-existent ngroup
    with pytest.raises(NgroupNotFoundError):
        await update_ngroup(req, uuid.uuid4(), mock_ngroup_update)

@pytest.mark.asyncio
async def test_delete_ngroup(make_request, connection_pool):
    """Test deleting a ngroup"""
    # Create an ngroup record
    req = make_request()

    mock_ngroup_create = NgroupCreate(short_name="test_ngroup", long_name="Test Ngroup")

    created_ngroup = await create_ngroup(req, mock_ngroup_create)

    # Delete the ngroup record
    await delete_ngroup(req, created_ngroup["id"])

    async with connection_pool.acquire() as conn:
        ngroup_id = await conn.fetchval("SELECT id FROM ngroup WHERE id = $1", created_ngroup["id"])
    
    # Verify that the record was deleted
    assert ngroup_id is None

    # Try to get the deleted record, expecting an error
    with pytest.raises(NgroupNotFoundError):
        await get_ngroup(req, created_ngroup["id"])

@pytest.mark.asyncio
async def test_delete_ngroup_not_found(make_request):
    """Test deleting a ngroup that does not exist."""
    # Try to delete a non-existent ngroup
    req = make_request()
    with pytest.raises(NgroupNotFoundError):
        await delete_ngroup(req, uuid.uuid4())

@pytest.mark.asyncio
async def test_list_ngroups(make_request):
    """Test getting a list of ngroups."""
    # Create multiple ngroup records
    req = make_request()

    mock_ngroup_create1 = NgroupCreate(short_name="test_ngroup", long_name="Test Ngroup")
    mock_ngroup_create2 = NgroupCreate(short_name="another_ngroup", long_name="Another NGroup")
    ngroup1 = await create_ngroup(req, mock_ngroup_create1)
    ngroup2 = await create_ngroup(req, mock_ngroup_create2)

    # List all ngroup records
    all_ngroups = await list_ngroups(req)

    # Check if the created records are in the list
    assert ngroup1["id"] in [n["id"] for n in all_ngroups]
    assert ngroup2["id"] in [n["id"] for n in all_ngroups]

@pytest.mark.asyncio
async def test_list_ngroup_for_form(make_request):
    """Test getting a list of ngroups for a form."""
    #Create multiple ngroup records
    req = make_request()

    mock_ngroup_create1 = NgroupCreate(short_name="test_ngroup", long_name="Test Ngroup")
    mock_ngroup_create2 = NgroupCreate(short_name="another_ngroup", long_name="Another NGroup")
    ngroup1 = await create_ngroup(req, mock_ngroup_create1)
    ngroup2 = await create_ngroup(req, mock_ngroup_create2)
    
    # List all ngroup for form
    all_ngroups = await list_ngroups_for_form(req)

    # Check if the created records are in the list
    assert ngroup1["id"] in [n["id"] for n in all_ngroups]
    assert ngroup2["id"] in [n["id"] for n in all_ngroups]

