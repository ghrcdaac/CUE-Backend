import pytest
import uuid

from app.v2.utils.collection import (create_collection, get_collection, list_collections,
                                     update_collection, delete_collection, CollectionNotFoundError)
from app.v2.type_util.collection import CollectionCreate,  CollectionUpdate 

@pytest.mark.asyncio
async def test_create_collection(make_request, connection_pool, make_collection_create, test_ngroup_id):
    """Test creating a collection."""
    req = make_request()
    req.state.pool = connection_pool
    mock_collection_create = make_collection_create("mock_collection")
    collection = await create_collection(req, mock_collection_create, test_ngroup_id)

    assert collection["ngroup_id"] == test_ngroup_id
    assert collection["short_name"] == mock_collection_create.short_name
    assert collection["provider_id"] == mock_collection_create.provider_id
    assert collection["egress_id"] == mock_collection_create.egress_id
    assert collection["active"] == mock_collection_create.active

@pytest.mark.asyncio
async def test_get_collection(make_request, make_collection_create, test_ngroup_id):
    """Test getting a collection."""
    req = make_request()

    mock_collection_create = make_collection_create("mock_collection")
    collection = await create_collection(req, mock_collection_create, test_ngroup_id)

    retrieved_collection = await get_collection(req, collection["id"])

    assert collection["id"] == retrieved_collection["id"]
    assert collection["short_name"] == retrieved_collection["short_name"]
    assert collection["provider_id"] == retrieved_collection["provider_id"]
    assert collection["egress_id"] == retrieved_collection["egress_id"]
    assert collection["active"] == retrieved_collection["active"]


@pytest.mark.asyncio
async def test_get_collection_not_found(make_request, connection_pool):
    """Test getting a collection that does not exist."""
    req = make_request()
    req.state.pool = connection_pool

    with pytest.raises(CollectionNotFoundError):
        await get_collection(req, uuid.uuid4())

@pytest.mark.asyncio
async def test_list_collection(make_request, make_collection_create, test_admin_user, test_ngroup_id):
    """Test getting a list of collections."""
    req = make_request()

    mock_collection_create1 = make_collection_create("mock_collection")
    mock_collection_create2 = make_collection_create("mock_collection2")
 
    collection1 = await create_collection(req, mock_collection_create1, test_ngroup_id)
    collection2 = await create_collection(req, mock_collection_create2, test_ngroup_id)

    all_collections = await list_collections(req, test_admin_user, str(test_ngroup_id))

    assert collection1["id"] in [c["id"] for c in all_collections]
    assert collection2["id"] in [c["id"] for c in all_collections]

@pytest.mark.asyncio
async def test_update_collection(make_request, make_collection_create, seed_provider, seed_egress, test_ngroup_id, test_admin_user):
    """Test updating a collection."""
    req = make_request()

    mock_collection_create = make_collection_create("mock_collection")

    collection = await create_collection(req, mock_collection_create, test_ngroup_id)
    new_provider = await seed_provider("new_provider", "New Provider", True, test_admin_user.id)
    new_egress = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"})

    mock_collection_update = CollectionUpdate(short_name="updated_mock_collection", active=False, provider_id=new_provider["id"], egress_id=new_egress["id"])

    updated_collection = await update_collection(req, collection["id"], mock_collection_update, collection)
    
    assert collection["id"] == updated_collection["id"]
    assert mock_collection_update.short_name == updated_collection["short_name"]
    assert mock_collection_update.active == updated_collection["active"]
    assert mock_collection_update.provider_id == updated_collection["provider_id"]
    assert mock_collection_update.egress_id == updated_collection["egress_id"]
    
@pytest.mark.asyncio
async def test_update_collection_not_found(make_request, test_ngroup_id):
    """Test updating a collection that does not exist."""
    req = make_request()

    mock_collection_update = CollectionUpdate(short_name="updated_mock_collection", active=False)

    with pytest.raises(CollectionNotFoundError):
        await update_collection(req, uuid.uuid4(), mock_collection_update, {"ngroup_id":test_ngroup_id})

@pytest.mark.asyncio
async def test_delete_collection(make_request, connection_pool, make_collection_create, test_ngroup_id):
    """Test deleting a collection."""
    req = make_request()

    mock_collection_create = make_collection_create("mock_collection")
    collection = await create_collection(req, mock_collection_create, test_ngroup_id)

    await delete_collection(req, collection["id"])

    async with connection_pool.acquire() as conn:
       collection_id = await conn.fetchval("SELECT id from collection WHERE id = $1", collection["id"])

    assert collection_id is None

@pytest.mark.asyncio
async def test_delete_collection_not_found(make_request):
    """Test deleting a collection that does not exist."""
    req = make_request()

    with pytest.raises(CollectionNotFoundError):
        await delete_collection(req, uuid.uuid4())
