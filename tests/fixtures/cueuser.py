import pytest

@pytest.fixture
def make_cueuser(test_ngroup_id, test_provider):
    def _make_cueuser(user_id, email, name, cueusername,
                      role_id="2068cc53-1232-4bc7-9647-3e29e6418e21", edpub_id=None,
                      ngroup_ids=[test_ngroup_id], provider_ids=[test_provider["id"]]):
        return {"user_id": user_id, "email": email, "name":name, "cueusername":cueusername,
                "role_id": role_id, "edpub_id":edpub_id, "ngroup_ids":ngroup_ids, "provider_ids":provider_ids }
    return _make_cueuser