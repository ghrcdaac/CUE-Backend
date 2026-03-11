import pytest
from app.v2.type_util.provider import ProviderCreate 
from uuid import UUID

@pytest.fixture
def make_provider_create(test_ngroup_id, test_admin_user):
    """Factory fixture for creating ProviderCreate objects."""
    def _make_provider_create(short_name: str,
                              long_name: str,
                              ngroup_id: UUID = test_ngroup_id, 
                              point_of_contact: UUID = test_admin_user.id,
                              can_upload: bool = True
                             ):
        return ProviderCreate(short_name=short_name,
                              long_name=long_name,
                              ngroup_id=ngroup_id,
                              point_of_contact=point_of_contact,
                              can_upload=can_upload)
    return _make_provider_create

