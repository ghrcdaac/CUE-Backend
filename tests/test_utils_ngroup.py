import pytest
from typing import Tuple
from unittest.mock import patch, MagicMock
import uuid
import os

from src.python.api.utils.ngroup import create_ngroup, get_ngroup, update_ngroup, delete_ngroup, list_ngroups, get_ngroup_id_by_name, NgroupNotFoundError
from src.python.lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn, NgroupUpdate

# Mock data for testing
@pytest.fixture
def mock_ngroup_create() -> NgroupCreate:
    return NgroupCreate(short_name="test_group", long_name="Test Group")

@pytest.fixture
def mock_ngroup_update() -> NgroupUpdate:
    return NgroupUpdate(short_name="updated_group", long_name="Updated Group")

@pytest.mark.asyncio
async def test_create_ngroup(mock_ngroup_create):
    result = await create_ngroup(mock_ngroup_create)
    assert isinstance(result, NgroupReturn)
    assert result.short_name == mock_ngroup_create.short_name
    assert result.long_name == mock_ngroup_create.long_name

@pytest.mark.asyncio
async def test_get_ngroup(mock_ngroup_create):
    # First, create an ngroup record
    created_ngroup = await create_ngroup(mock_ngroup_create)

    # Then, try to get it
    retrieved_ngroup = await get_ngroup(created_ngroup.id)
    assert retrieved_ngroup.id == created_ngroup.id
    assert retrieved_ngroup.short_name == created_ngroup.short_name
    assert retrieved_ngroup.long_name == created_ngroup.long_name

@pytest.mark.asyncio
async def test_get_ngroup_not_found():
    # Try to get a non-existent ngroup
    with pytest.raises(NgroupNotFoundError):
        await get_ngroup(uuid.uuid4())

@pytest.mark.asyncio
async def test_update_ngroup(mock_ngroup_create, mock_ngroup_update):
    # Create an ngroup record
    created_ngroup = await create_ngroup(mock_ngroup_create)

    # Update the ngroup record
    updated_ngroup = await update_ngroup(created_ngroup.id, mock_ngroup_update)

    # Check if the record was updated
    assert updated_ngroup.id == created_ngroup.id
    assert updated_ngroup.short_name == mock_ngroup_update.short_name
    assert updated_ngroup.long_name == mock_ngroup_update.long_name

@pytest.mark.asyncio
async def test_update_ngroup_not_found(mock_ngroup_update):
    # Try to update a non-existent ngroup
    with pytest.raises(NgroupNotFoundError):
        await update_ngroup(uuid.uuid4(), mock_ngroup_update)

@pytest.mark.asyncio
async def test_delete_ngroup(mock_ngroup_create):
    # Create an ngroup record
    created_ngroup = await create_ngroup(mock_ngroup_create)

    # Delete the ngroup record
    success = await delete_ngroup(created_ngroup.id)

    # Verify that the record was deleted
    assert success is True

    # Try to get the deleted record, expecting an error
    with pytest.raises(NgroupNotFoundError):
        await get_ngroup(created_ngroup.id)

@pytest.mark.asyncio
async def test_delete_ngroup_not_found():
    # Try to delete a non-existent ngroup
    with pytest.raises(NgroupNotFoundError):
        await delete_ngroup(uuid.uuid4())

@pytest.mark.asyncio
async def test_list_ngroups(mock_ngroup_create):
    # Create multiple ngroup records
    ngroup1 = await create_ngroup(mock_ngroup_create)
    ngroup2 = await create_ngroup(NgroupCreate(short_name="another_group", long_name="Another Group"))

    # List all ngroup records
    all_ngroups = await list_ngroups()

    # Check if the created records are in the list
    assert ngroup1.id in [n.id for n in all_ngroups]
    assert ngroup2.id in [n.id for n in all_ngroups]

@pytest.mark.asyncio
async def test_get_ngroup_id_by_name(mock_ngroup_create):
    # Create an ngroup record
    created_ngroup = await create_ngroup(mock_ngroup_create)

    # Get the ngroup ID by short_name
    ngroup_id_short = await get_ngroup_id_by_name(short_name=created_ngroup.short_name)
    assert ngroup_id_short == created_ngroup.id

    # Get the ngroup ID by long_name
    ngroup_id_long = await get_ngroup_id_by_name(long_name=created_ngroup.long_name)
    assert ngroup_id_long == created_ngroup.id

@pytest.mark.asyncio
async def test_get_ngroup_id_by_name_not_found(mock_ngroup_create):
    # Create an ngroup record
    created_ngroup = await create_ngroup(mock_ngroup_create)

    # Try to get ID with non-existent short_name
    with pytest.raises(NgroupNotFoundError):
        await get_ngroup_id_by_name(short_name="nonexistent")

    # Try to get ID with non-existent long_name
    with pytest.raises(NgroupNotFoundError):
        await get_ngroup_id_by_name(long_name="Nonexistent Group")