import pytest
from unittest.mock import AsyncMock, patch
from typing import Tuple
import uuid
import json
from asyncpg.exceptions import UniqueViolationError, DataError, ForeignKeyViolationError

from ..lambda_utils.database_util.db_util import query, get_connection_pool
from ..lambda_utils.database_util import ngroup as ngroup_db
from ..lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn, NgroupUpdate

# Mock data for ngroup testing
@pytest.fixture
def mock_ngroup_data() -> NgroupCreate:
    return NgroupCreate(short_name="test_group", long_name="Test Group")

@pytest.fixture
def mock_ngroup_return(mock_ngroup_data) -> NgroupReturn:
    return NgroupReturn(id=uuid.uuid4(), **mock_ngroup_data.model_dump())

@pytest.mark.asyncio
async def test_create_ngroup_in_db(db_connection, mock_ngroup_data, mock_ngroup_return):
    # Mock data for testing
    params = (mock_ngroup_return.id, mock_ngroup_data.short_name, mock_ngroup_data.long_name)

    # Execute the function
    await ngroup_db.create_ngroup_in_db(db_connection, params)

    # Fetch the inserted data to verify insertion
    rows = await db_connection.fetch("SELECT id, short_name, long_name FROM ngroup")

    # Map the fetched rows to NgroupReturn objects
    inserted_data = [NgroupReturn.from_db_row(row) for row in rows]

    # Verify that one record was inserted and the data matches
    assert len(inserted_data) == 1
    inserted_record = inserted_data[0]
    assert inserted_record.id == mock_ngroup_return.id
    assert inserted_record.short_name == mock_ngroup_data.short_name
    assert inserted_record.long_name == mock_ngroup_data.long_name

@pytest.mark.asyncio
async def test_create_ngroup_in_db_unique_violation(db_connection, mock_ngroup_data, mock_ngroup_return):
    # Mock data for testing
    params = (mock_ngroup_return.id, mock_ngroup_data.short_name, mock_ngroup_data.long_name)

    # Execute the function twice to trigger a unique constraint violation
    await ngroup_db.create_ngroup_in_db(db_connection, params)
    with pytest.raises(UniqueViolationError):
        await ngroup_db.create_ngroup_in_db(db_connection, params)

@pytest.mark.asyncio
async def test_create_ngroup_in_db_data_error(db_connection, mock_ngroup_return):
    # Mock data with a long name exceeding the database limit to trigger a data error
    invalid_long_name = "a" * 256  # Assuming the limit is less than 256
    params = (mock_ngroup_return.id, "valid_short_name", invalid_long_name)

    # Execute the function and expect a DataError
    with pytest.raises(DataError):
        await ngroup_db.create_ngroup_in_db(db_connection, params)

@pytest.mark.asyncio
async def test_get_ngroup_id_from_db(db_connection, mock_ngroup_return):
    # Insert a record to be fetched
    insert_params = (mock_ngroup_return.id, mock_ngroup_return.short_name, mock_ngroup_return.long_name)
    await db_connection.execute(
        "INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $2, $3)",
        *insert_params
    )

    # Execute the function with the short_name of the inserted record
    params = (mock_ngroup_return.short_name, None)
    fetched_id = await ngroup_db.get_ngroup_id_from_db(db_connection, params)

    # Verify that the correct ID was fetched
    assert fetched_id == mock_ngroup_return.id

@pytest.mark.asyncio
async def test_get_ngroup_id_from_db_not_found(db_connection):
    # Execute the function with non-existent names
    params = ("nonexistent_short_name", "nonexistent_long_name")
    fetched_id = await ngroup_db.get_ngroup_id_from_db(db_connection, params)

    # Verify that None is returned when no matching record is found
    assert fetched_id is None

@pytest.mark.asyncio
async def test_get_ngroup_from_db(db_connection, mock_ngroup_return):
    # Insert a record to be fetched
    insert_params = (mock_ngroup_return.id, mock_ngroup_return.short_name, mock_ngroup_return.long_name)
    await db_connection.execute(
        "INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $2, $3)",
        *insert_params
    )

    # Execute the function with the ID of the inserted record
    params = (mock_ngroup_return.id,)
    fetched_records = await ngroup_db.get_ngroup_from_db(db_connection, params)

    # Map the fetched rows to NgroupReturn objects
    fetched_data = [NgroupReturn.from_db_row(row) for row in fetched_records]

    # Verify that one record was fetched and the data matches
    assert len(fetched_data) == 1
    fetched_record = fetched_data[0]
    assert fetched_record.id == mock_ngroup_return.id
    assert fetched_record.short_name == mock_ngroup_return.short_name
    assert fetched_record.long_name == mock_ngroup_return.long_name

@pytest.mark.asyncio
async def test_get_ngroup_from_db_not_found(db_connection):
    # Execute the function with a non-existent ID
    params = (uuid.uuid4(),)
    fetched_records = await ngroup_db.get_ngroup_from_db(db_connection, params)

    # Verify that no record was fetched
    assert len(fetched_records) == 0

@pytest.mark.asyncio
async def test_update_ngroup_in_db(db_connection, mock_ngroup_return):
    # Insert a record to be updated
    insert_params = (mock_ngroup_return.id, mock_ngroup_return.short_name, mock_ngroup_return.long_name)
    await db_connection.execute(
        "INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $2, $3)",
        *insert_params
    )

    # New data for update
    new_short_name = "updated_short_name"
    new_long_name = "updated_long_name"

    # Update the record
    update_params = (mock_ngroup_return.id, new_short_name, new_long_name)
    await ngroup_db.update_ngroup_in_db(db_connection, update_params)

    # Fetch the updated record
    params = (mock_ngroup_return.id,)
    fetched_records = await db_connection.fetch("SELECT id, short_name, long_name FROM ngroup WHERE id = $1", *params)

    # Map the fetched rows to NgroupReturn objects
    updated_data = [NgroupReturn.from_db_row(row) for row in fetched_records]

    # Verify that the record was updated correctly
    assert len(updated_data) == 1
    updated_record = updated_data[0]
    assert updated_record.id == mock_ngroup_return.id
    assert updated_record.short_name == new_short_name
    assert updated_record.long_name == new_long_name

@pytest.mark.asyncio
async def test_update_ngroup_in_db_not_found(db_connection):
    # Attempt to update a non-existent record
    non_existent_id = uuid.uuid4()
    update_params = (non_existent_id, "updated_short_name", "updated_long_name")
    
    # Execute the update function
    updated_records = await ngroup_db.update_ngroup_in_db(db_connection, update_params)

    # Verify that no record was updated
    assert len(updated_records) == 0

@pytest.mark.asyncio
async def test_delete_ngroup_from_db(db_connection, mock_ngroup_return):
    # Insert a record to be deleted
    insert_params = (mock_ngroup_return.id, mock_ngroup_return.short_name, mock_ngroup_return.long_name)
    await db_connection.execute(
        "INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $2, $3)",
        *insert_params
    )

    # Delete the record
    params = (mock_ngroup_return.id,)
    result = await ngroup_db.delete_ngroup_from_db(db_connection, params)

    # Verify that the record was deleted
    assert result is True

    # Verify that the record no longer exists
    select_params = (mock_ngroup_return.id,)
    remaining_records = await db_connection.fetch("SELECT * FROM ngroup WHERE id = $1", *select_params)
    assert len(remaining_records) == 0

@pytest.mark.asyncio
async def test_delete_ngroup_from_db_not_found(db_connection):
    # Attempt to delete a non-existent record
    non_existent_id = uuid.uuid4()
    params = (non_existent_id,)
    result = await ngroup_db.delete_ngroup_from_db(db_connection, params)

    # Verify that the result indicates no record was deleted
    assert result is False

@pytest.mark.asyncio
async def test_list_ngroups_from_db(db_connection, mock_ngroup_return):
    # Insert multiple records
    for i in range(3):
        insert_params = (uuid.uuid4(), f"short_name_{i}", f"long_name_{i}")
        await db_connection.execute(
            "INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $2, $3)",
            *insert_params
        )

    # Execute the list function
    fetched_records = await ngroup_db.list_ngroups_from_db(db_connection, ())

    # Map the fetched rows to NgroupReturn objects
    listed_data = [NgroupReturn.from_db_row(row) for row in fetched_records]

    # Verify that all inserted records are fetched
    assert len(listed_data) >= 3  # Check if at least 3 records are fetched

    # You can add more specific checks if needed, for example, checking the short_names or long_names