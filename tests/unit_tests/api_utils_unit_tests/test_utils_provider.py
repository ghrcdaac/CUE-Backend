import pytest
import uuid

from app.v2.utils.provider import (create_provider, get_provider, list_providers,
                                   list_providers_for_form, update_provider, delete_provider, ProviderNotFoundError)
from app.v2.type_util.provider import ProviderUpdate

@pytest.mark.asyncio
async def test_create_provider(make_request, make_provider_create):
    """Test creating a provider."""
    req = make_request()
    mock_provider_create = make_provider_create("test_provider","Test Provider")

    created_provider = await create_provider(req, mock_provider_create)
 
    assert created_provider["ngroup_id"] == mock_provider_create.ngroup_id
    assert created_provider["point_of_contact"] == mock_provider_create.point_of_contact
    assert created_provider["short_name"] == mock_provider_create.short_name
    assert created_provider["long_name"] == mock_provider_create.long_name
    assert created_provider["can_upload"] == mock_provider_create.can_upload

@pytest.mark.asyncio
async def test_create_provider_point_of_contact_does_not_exist(make_request, make_provider_create):
    """Test creating a provider, but point of contact does not exist."""
    req = make_request()
    mock_provider_create = make_provider_create("test_provider","Test Provider", point_of_contact=uuid.uuid4())

    with pytest.raises(ValueError):
        await create_provider(req, mock_provider_create)
 

@pytest.mark.asyncio
async def test_get_provider(make_request, make_provider_create):
    """Test getting a provider."""
    req = make_request()

    mock_provider_create = make_provider_create("test_provider","Test Provider")
    created_provider = await create_provider(req, mock_provider_create)

    retrieved_provider = await get_provider(req, created_provider["id"])

    assert retrieved_provider["id"] == created_provider["id"]
    assert retrieved_provider["point_of_contact"] == created_provider["point_of_contact"]
    assert retrieved_provider["short_name"] == created_provider["short_name"]
    assert retrieved_provider["long_name"] == created_provider["long_name"]
    assert retrieved_provider["can_upload"] == created_provider["can_upload"]

@pytest.mark.asyncio
async def test_list_providers(make_request, make_provider_create, test_admin_user, test_ngroup_id):
    """Test getting a list of providers."""
    req = make_request()

    mock_provider_create1 = make_provider_create("test_provider","Test Provider")
    mock_provider_create2 = make_provider_create("test_provider2","Test Provider2")

    provider1 = await create_provider(req, mock_provider_create1)
    provider2 = await create_provider(req, mock_provider_create2)

    all_providers = await list_providers(req, test_admin_user, active_ngroup_id=str(test_ngroup_id))

    assert provider1["id"] in [p["id"] for p in all_providers]
    assert provider2["id"] in [p["id"] for p in all_providers]

@pytest.mark.asyncio
async def test_list_providers_for_form(make_request, connection_pool, make_provider_create, test_ngroup_id):
    """Test getting a list of provider for a form."""
    req = make_request()
    req.state.pool = connection_pool

    mock_provider_create1 = make_provider_create("test_provider","Test Provider")
    mock_provider_create2 = make_provider_create("test_provider2","Test Provider2")

    provider1 = await create_provider(req, mock_provider_create1)
    provider2 = await create_provider(req, mock_provider_create2)

    all_providers = await list_providers_for_form(req, test_ngroup_id)

    assert provider1["id"] in [p["id"] for p in all_providers]
    assert provider2["id"] in [p["id"] for p in all_providers]

@pytest.mark.asyncio
async def test_update_provider(make_request, make_provider_create, test_daac_manager_user):
    """Test updating a provider."""
    req = make_request()

    mock_provider_create = make_provider_create("test_provider","Test Provider")

    mock_provider_update = ProviderUpdate(short_name="new_provider_name",
                                          long_name="New Provider Name",
                                          can_upload=True,
                                          point_of_contact=test_daac_manager_user.id)

    provider = await create_provider(req, mock_provider_create)
    updated_provider = await update_provider(req, provider["id"], mock_provider_update)

    assert updated_provider["id"] == provider["id"]
    assert updated_provider["short_name"] == mock_provider_update.short_name
    assert updated_provider["long_name"] == mock_provider_update.long_name
    assert updated_provider["can_upload"] == mock_provider_update.can_upload
    assert updated_provider["point_of_contact"] == mock_provider_update.point_of_contact

@pytest.mark.asyncio
async def test_update_provider_empty_update(make_request, make_provider_create):
    """Test updating a provider with a empty update."""
    req = make_request()

    mock_provider_create = make_provider_create("test_provider","Test Provider")

    mock_provider_update = ProviderUpdate()

    provider = await create_provider(req, mock_provider_create)
    with pytest.raises(ValueError):
        await update_provider(req, provider["id"], mock_provider_update)

@pytest.mark.asyncio
async def test_update_provider_new_point_of_contact_does_not_exist(make_request, connection_pool, make_provider_create):
    """Testing updating a provider but the point of contact does not exist."""
    req = make_request()

    mock_provider_create = make_provider_create("test_provider","Test Provider")

    mock_provider_update = ProviderUpdate(short_name="new_provider_name",
                                          long_name="New Provider Name",
                                          can_upload=False,
                                          point_of_contact=uuid.uuid4())

    provider = await create_provider(req, mock_provider_create)
    with pytest.raises(ValueError):
        await update_provider(req, provider["id"], mock_provider_update)

@pytest.mark.asyncio
async def test_update_provider_provider_does_not_exist(make_request, connection_pool, make_provider_create, test_daac_manager_user):
    """Test updating a provider, but provider does not exist."""
    req = make_request()
    req.state.pool = connection_pool

    mock_provider_update = ProviderUpdate(short_name="new_provider_name",
                                          long_name="New Provider Name",
                                          can_upload=False,
                                          reason="Test",
                                          point_of_contact=test_daac_manager_user.id)

    with pytest.raises(ProviderNotFoundError):
        await update_provider(req, uuid.uuid4(), mock_provider_update)


@pytest.mark.asyncio
async def test_delete_provider(make_request, connection_pool, make_provider_create):
    """Test deleting a provider"""
    req = make_request()
    req.state.pool = connection_pool

    mock_provider_create = make_provider_create("test_provider","Test Provider")

    provider = await create_provider(req, mock_provider_create)

    await delete_provider(req, provider["id"])

    async with connection_pool.acquire() as conn:
        provider_id = await conn.fetchval("SELECT id FROM provider WHERE id = $1", provider["id"])

    assert provider_id is None

    with pytest.raises(ProviderNotFoundError):
        await get_provider(req, provider["id"])


@pytest.mark.asyncio
async def test_delete_provider_provider_not_found(make_request, connection_pool, make_provider_create):
    """Test deleing a provider, but the provider does exist."""
    req = make_request()
    req.state.pool = connection_pool

    with pytest.raises(ProviderNotFoundError):
        await delete_provider(req, uuid.uuid4())
