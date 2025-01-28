import pytest
import asyncio
import asyncpg
from typing import Tuple
from unittest.mock import AsyncMock
import os
import uuid

from ..lambda_utils.database_util.db_util import get_connection_pool, setup_connection
from ..lambda_utils.type_util.egress import EgressCreate, EgressReturn
from ..lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn

# Set environment variables for testing
os.environ['PG_DB'] = os.getenv('PG_DB_TEST', 'your_test_database_name')
os.environ['PG_USER'] = os.getenv('PG_USER_TEST', 'your_test_database_user')
os.environ['PG_PASS'] = os.getenv('PG_PASS_TEST', 'your_test_database_password')
os.environ['PG_HOST'] = os.getenv('PG_HOST_TEST', 'your_test_database_host')
os.environ['PG_PORT'] = os.getenv('PG_PORT_TEST', '5432')  # Ensure this is a string
# Set an environment variable for the test ngroup ID
os.environ['TEST_NGROUP_ID'] = str(uuid.uuid4())

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def connection_pool():
    """Create a connection pool for the test session."""
    pool = await get_connection_pool(setup=setup_connection)
    yield pool
    await pool.close()

@pytest.fixture
async def db_connection(connection_pool):
    """Get a connection from the pool for each test."""
    async with connection_pool.acquire() as conn:
        yield conn

@pytest.fixture
async def test_ngroup_id(db_connection):
    """Create a test ngroup and return its ID."""
    ngroup_id = uuid.uuid4()
    # Insert a test ngroup record to be used by other tests
    insert_params = (ngroup_id, "test_group", "Test Group")
    await db_connection.execute(
        "INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $2, $3)",
        *insert_params
    )
    return ngroup_id

# Mock data for egress testing
@pytest.fixture
def mock_egress_data(test_ngroup_id) -> EgressCreate:
    return EgressCreate(type="s3", path="some/path", config={"key": "value"}, ngroup_id=test_ngroup_id)

@pytest.fixture
def mock_egress_return(mock_egress_data) -> EgressReturn:
    return EgressReturn(id=uuid.uuid4(), **mock_egress_data.model_dump())

# Mock data for ngroup testing
@pytest.fixture
def mock_ngroup_data() -> NgroupCreate:
    return NgroupCreate(short_name="test_group", long_name="Test Group")

@pytest.fixture
def mock_ngroup_return(mock_ngroup_data) -> NgroupReturn:
    return NgroupReturn(id=uuid.uuid4(), **mock_ngroup_data.model_dump())