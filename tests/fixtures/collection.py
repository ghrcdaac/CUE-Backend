import pytest
from app.v2.type_util.collection import CollectionCreate

@pytest.fixture
def make_collection_create(test_provider, test_egress):
    def _make_collection_create(short_name, active=True, provider_id=test_provider["id"], egress_id=test_egress["id"]):
        return CollectionCreate(short_name=short_name,
                                active=active,
                                provider_id=provider_id,
                                egress_id=egress_id)
    return _make_collection_create