import pytest

# Import your functions from utils/egress.py
from  app.v2.utils.egress import create_egress, get_egress, update_egress, list_egresses, delete_egress, EgressNotFoundError
from app.v2.type_util.egress import EgressCreate, EgressUpdate


@pytest.mark.asyncio
async def test_create_egress(make_request, test_ngroup_id):
    """Test creating a egress."""
    req = make_request()
    mock_egress_create = EgressCreate(type="s3", path="some/path", config={"key": "value"})
    result = await create_egress(req, mock_egress_create, ngroup_id=test_ngroup_id)
    assert isinstance(result, dict)
    assert result['type'] == mock_egress_create.type
    assert result['path'] == mock_egress_create.path
    assert result['config'] == mock_egress_create.config
    assert result['ngroup_id'] == test_ngroup_id

@pytest.mark.asyncio
async def test_get_egress(make_request, test_ngroup_id):
    """Test getting a egress."""
    # First, create an egress record
    req = make_request()
    mock_egress_create = EgressCreate(type="s3", path="some/path", config={"key": "value"})
    created_egress = await create_egress(req, mock_egress_create, ngroup_id=test_ngroup_id)

    # Then, try to get it
    retrieved_egress = await get_egress(req, created_egress.get('id') )
    assert retrieved_egress["id"] == created_egress["id"]
    assert retrieved_egress["type"] == created_egress["type"]
    assert retrieved_egress["path"] == created_egress["path"]
    assert retrieved_egress["config"] == created_egress["config"]
    assert retrieved_egress["ngroup_id"] == test_ngroup_id

@pytest.mark.asyncio
async def test_update_egress(make_request, test_ngroup_id):
    """Test updating an egress."""
    # Create an egress record
    req = make_request()
    mock_egress_create = EgressCreate(type="s3", path="some/path", config={"key": "value"})
    created_egress = await create_egress(req, mock_egress_create, ngroup_id=test_ngroup_id)

    # Update the egress record

    mock_egress_update = EgressUpdate(type="new_type", path="new/path", config={"key": "new_value"})
    updated_egress = await update_egress(req, created_egress["id"], mock_egress_update)

    # Check if the record was updated
    # assert updated_egress.get("id") == created_egress.get("id")
    assert updated_egress["type"] == mock_egress_update.type
    assert updated_egress["path"] == mock_egress_update.path
    assert updated_egress["config"] == mock_egress_update.config
    #assert updated_egress.get("ngroup_id") == mock_egress_update.get("ngroup_id")

@pytest.mark.asyncio
async def test_list_egresses(make_request, connection_pool, test_admin_user, test_ngroup_id):
    """Test listing egresses."""
    # Create multiple egress records
    req = make_request()
    mock_egress_create1 = EgressCreate(type="s3", path="some/path", config={"key": "value"})
    mock_egress_create2 = EgressCreate(type="gcp", path="another/path", config={"key": "another_value"})
    egress1 = await create_egress(req, mock_egress_create1, ngroup_id=test_ngroup_id)
    egress2 = await create_egress(req, mock_egress_create2, ngroup_id=test_ngroup_id)

    # List all egress records
    all_egresses = await list_egresses(req, test_admin_user, str(test_ngroup_id))

    # Check if the created records are in the list
    assert egress1["id"] in [e["id"] for e in all_egresses]
    assert egress2["id"] in [e["id"] for e in all_egresses]

@pytest.mark.asyncio
async def test_delete_egress(make_request, connection_pool, test_ngroup_id):
    """Test deleting an egress."""
    # Create an egress record
    req = make_request()
    mock_egress_create = EgressCreate(type="s3", path="some/path", config={"key": "value"})
    created_egress = await create_egress(req, mock_egress_create, ngroup_id=test_ngroup_id)

    # Delete the egress record
    await delete_egress(req, created_egress.get("id"))

    # Verify that the record was deleted
    async with connection_pool.acquire() as conn:
        egress_id = await conn.fetchval("SELECT id FROM egress WHERE id = $1", created_egress.get("id"))
    
    assert egress_id is None

    # Try to get the deleted record, expecting Exception 
    get_req = make_request()
    get_req.state.pool = connection_pool
    egress = None
    try:
        egress = await get_egress(get_req, created_egress.get("id"))
    except Exception as e:
        assert isinstance(e, EgressNotFoundError) == True
    finally:
        assert egress is None 