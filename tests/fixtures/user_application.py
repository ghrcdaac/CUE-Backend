import pytest
from app.v2.type_util.user_application import UserApplicationCreate
from pydantic import EmailStr
from uuid import UUID
from typing import Optional


@pytest.fixture
def make_user_application_create(test_provider, test_ngroup_id):
    """Factory fixture for creating UserApplicationCreate objects.""" 
    def _make_user_application_create(email: EmailStr, name: str, username: str,
                                      justification: str, account_type: str, ngroup_id: UUID = test_ngroup_id,
                                       provider_id: Optional[UUID] = test_provider["id"], edpub_id: Optional[UUID] = None):
        return UserApplicationCreate(email=email,
                                     name=name,
                                     username=username,
                                     justification=justification,
                                     account_type=account_type,
                                     ngroup_id=ngroup_id,
                                     provider_id=provider_id,
                                     edpub_id=edpub_id)
    return _make_user_application_create

