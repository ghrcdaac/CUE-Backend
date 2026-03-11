import pytest
from uuid import UUID
from app.v2.type_util.collection import CollectionCreate

@pytest.fixture
def make_collection_create(test_provider, test_egress):
    """Fixture for creating CollectionCreate"""
    def _make_collection_create(short_name:str, active:bool=True, provider_id:UUID=test_provider["id"], egress_id:UUID=test_egress["id"]):
        return CollectionCreate(short_name=short_name,
                                active=active,
                                provider_id=provider_id,
                                egress_id=egress_id)
    return _make_collection_create