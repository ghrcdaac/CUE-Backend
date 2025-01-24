import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Tuple
import uuid
import json

from src.python.lambda_utils.database_util.db_util import query, get_connection_pool
from src.python.lambda_utils.database_util import egress as egress_db
from src.python.lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate

# Mock data for egress testing
@pytest.fixture
def mock_egress_data() -> EgressCreate:
    return EgressCreate(type="s3", path="some/path", config={"key": "value"}, ngroup_id=uuid.uuid4())

@pytest.fixture
def mock_egress_return(mock_egress_data) -> EgressReturn:
    return EgressReturn(id=uuid.uuid4(), **mock_egress_data.model_dump())

@pytest.mark.asyncio
async def test_query_with_row_mapper(db_connection, mock_egress_return):
    # Mock the database operation to return a specific result
    mock_operation = AsyncMock(return_value=[(mock_egress_return.id, mock_egress_return.type, mock_egress_return.path, json.dumps(mock_egress_return.config), mock_egress_return.ngroup_id)])

    # Call the query function with the mock operation and row mapper
    pool = await get_connection_pool()
    result = await query(pool, mock_operation, row_mapper=EgressReturn.from_db_row)
    await pool.close()

    # Assert that the operation was called and the result is as expected
    mock_operation.assert_awaited_once()
    assert len(result) == 1
    assert isinstance(result[0], EgressReturn)
    assert result[0] == mock_egress_return

@pytest.mark.asyncio
async def test_create_egress_in_db(db_connection, mock_egress_data, mock_egress_return):
    # Mock data for testing
    params = (mock_egress_data.type, mock_egress_data.path, mock_egress_data.config, mock_egress_data.ngroup_id)
    
    # Execute the function
    await egress_db.create_egress_in_db(db_connection, params)

    # Fetch the inserted data to verify insertion
    rows = await db_connection.fetch("SELECT id, type, path, config, ngroup_id FROM egress")
    
    # Map the fetched rows to EgressReturn objects
    inserted_data = [EgressReturn.from_db_row(row) for row in rows]

    # Verify that one record was inserted and the data matches
    assert len(inserted_data) == 1
    inserted_record = inserted_data[0]
    assert inserted_record.type == mock_egress_data.type
    assert inserted_record.path == mock_egress_data.path
    assert inserted_record.config == mock_egress_data.config
    assert inserted_record.ngroup_id == mock_egress_data.ngroup_id

@pytest.mark.asyncio
async def test_get_egress_from_db(db_connection, mock_egress_return):
    # Insert a record to be fetched
    insert_params = (mock_egress_return.id, mock_egress_return.type, mock_egress_return.path, json.dumps(mock_egress_return.config), mock_egress_return.ngroup_id)
    await db_connection.execute(
        "INSERT INTO egress (id, type, path, config, ngroup_id) VALUES ($1, $2, $3, $4, $5)",
        *insert_params
    )

    # Execute the function with the ID of the inserted record
    params = (mock_egress_return.id,)
    fetched_records = await egress_db.get_egress_from_db(db_connection, params)

    # Map the fetched rows to EgressReturn objects
    fetched_data = [EgressReturn.from_db_row(row) for row in fetched_records]

    # Verify that one record was fetched and the data matches
    assert len(fetched_data) == 1
    fetched_record = fetched_data[0]
    assert fetched_record.id == mock_egress_return.id
    assert fetched_record.type == mock_egress_return.type
    assert fetched_record.path == mock_egress_return.path
    assert fetched_record.config == mock_egress_return.config
    assert fetched_record.ngroup_id == mock_egress_return.ngroup_id

@pytest.mark.asyncio
async def test_update_egress_in_db(db_connection, mock_egress_return):
    # Insert a record to be updated
    insert_params = (mock_egress_return.id, mock_egress_return.type, mock_egress_return.path, json.dumps(mock_egress_return.config), mock_egress_return.ngroup_id)
    await db_connection.execute(
        "INSERT INTO egress (id, type, path, config, ngroup_id) VALUES ($1, $2, $3, $4, $5)",
        *insert_params
    )

    # New data for update
    new_type = "updated_type"
    new_path = "updated/path"
    new_config = {"key": "updated_value"}

    # Update the record
    update_params = ({"type": new_type, "path": new_path, "config": new_config}, mock_egress_return.id)
    await egress_db.update_egress_in_db(db_connection, update_params)

    # Fetch the updated record
    params = (mock_egress_return.id,)
    fetched_records = await db_connection.fetch("SELECT id, type, path, config, ngroup_id FROM egress WHERE id = $1", *params)

    # Map the fetched rows to EgressReturn objects
    updated_data = [EgressReturn.from_db_row(row) for row in fetched_records]

    # Verify that the record was updated correctly
    assert len(updated_data) == 1
    updated_record = updated_data[0]
    assert updated_record.id == mock_egress_return.id
    assert updated_record.type == new_type
    assert updated_record.path == new_path
    assert updated_record.config == new_config
    assert updated_record.ngroup_id == mock_egress_return.ngroup_id

@pytest.mark.asyncio
async def test_list_egresses_from_db(db_connection, mock_egress_return):
    # Insert multiple records
    for i in range(3):
        insert_params = (uuid.uuid4(), f"type_{i}", f"path_{i}", json.dumps({"key": f"value_{i}"}), mock_egress_return.ngroup_id)
        await db_connection.execute(
            "INSERT INTO egress (id, type, path, config, ngroup_id) VALUES ($1, $2, $3, $4, $5)",
            *insert_params
        )

    # Execute the list function
    fetched_records = await egress_db.list_egresses_from_db(db_connection, ())

    # Map the fetched rows to EgressReturn objects
    listed_data = [EgressReturn.from_db_row(row) for row in fetched_records]

    # Verify that all inserted records are fetched
    assert len(listed_data) >= 3  # Check if at least 3 records are fetched

@pytest.mark.asyncio
async def test_delete_egress_from_db(db_connection, mock_egress_return):
    # Insert a record to be deleted
    insert_params = (mock_egress_return.id, mock_egress_return.type, mock_egress_return.path, json.dumps(mock_egress_return.config), mock_egress_return.ngroup_id)
    await db_connection.execute(
        "INSERT INTO egress (id, type, path, config, ngroup_id) VALUES ($1, $2, $3, $4, $5)",
        *insert_params
    )

    # Delete the record
    params = (mock_egress_return.id,)
    result = await egress_db.delete_egress_from_db(db_connection, params)

    # Verify that the record was deleted
    assert result is True

    # Verify that the record no longer exists
    select_params = (mock_egress_return.id,)
    remaining_records = await db_connection.fetch("SELECT * FROM egress WHERE id = $1", *select_params)
    assert len(remaining_records) == 0