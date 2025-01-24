import pytest
from typing import Tuple
from unittest.mock import patch, MagicMock
import uuid
import os

# Import your functions from utils/egress.py
from ..utils.egress import create_egress, get_egress, update_egress, list_egresses, delete_egress
from ..lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate

# Mock data for testing
@pytest.fixture
def mock_egress_create() -> EgressCreate:
    return EgressCreate(type="s3", path="some/path", config={"key": "value"}, ngroup_id=uuid.UUID(os.getenv("TEST_NGROUP_ID")))

@pytest.fixture
def mock_egress_update() -> EgressUpdate:
    return EgressUpdate(type="new_type", path="new/path", config={"key": "new_value"}, ngroup_id=uuid.UUID(os.getenv("TEST_NGROUP_ID")))

@pytest.mark.asyncio
async def test_create_egress(mock_egress_create):
    result = await create_egress(mock_egress_create)
    assert isinstance(result, EgressReturn)
    assert result.type == mock_egress_create.type
    assert result.path == mock_egress_create.path
    assert result.config == mock_egress_create.config
    assert result.ngroup_id == mock_egress_create.ngroup_id

@pytest.mark.asyncio
async def test_get_egress(mock_egress_create):
    # First, create an egress record
    created_egress = await create_egress(mock_egress_create)

    # Then, try to get it
    retrieved_egress = await get_egress(created_egress.id)
    assert retrieved_egress.id == created_egress.id
    assert retrieved_egress.type == created_egress.type
    assert retrieved_egress.path == created_egress.path
    assert retrieved_egress.config == created_egress.config
    assert retrieved_egress.ngroup_id == created_egress.ngroup_id

@pytest.mark.asyncio
async def test_update_egress(mock_egress_create, mock_egress_update):
    # Create an egress record
    created_egress = await create_egress(mock_egress_create)

    # Update the egress record
    updated_egress = await update_egress(created_egress.id, mock_egress_update)

    # Check if the record was updated
    assert updated_egress.id == created_egress.id
    assert updated_egress.type == mock_egress_update.type
    assert updated_egress.path == mock_egress_update.path
    assert updated_egress.config == mock_egress_update.config
    assert updated_egress.ngroup_id == mock_egress_update.ngroup_id

@pytest.mark.asyncio
async def test_list_egresses(mock_egress_create):
    # Create multiple egress records
    egress1 = await create_egress(mock_egress_create)
    egress2 = await create_egress(EgressCreate(type="gcp", path="another/path", config={"key": "another_value"}, ngroup_id=uuid.UUID(os.getenv("TEST_NGROUP_ID"))))

    # List all egress records
    all_egresses = await list_egresses()

    # Check if the created records are in the list
    assert egress1.id in [e.id for e in all_egresses]
    assert egress2.id in [e.id for e in all_egresses]

@pytest.mark.asyncio
async def test_delete_egress(mock_egress_create):
    # Create an egress record
    created_egress = await create_egress(mock_egress_create)

    # Delete the egress record
    success = await delete_egress(created_egress.id)

    # Verify that the record was deleted
    assert success is True

    # Try to get the deleted record, expecting None
    deleted_egress = await get_egress(created_egress.id)
    assert deleted_egress is None