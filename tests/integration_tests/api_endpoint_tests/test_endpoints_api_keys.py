import pytest
import uuid 
from datetime import datetime
from app.v2.utils.api_keys import ApiKeyNotFoundError, ApiKeyPermissionError 

def test_create_api_key_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    """Test create api key endpoint."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request= {"name": "test_key",
                             "key_type": "personal",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "ngroup_id": str(test_ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    response_json = response.json()
    assert response_json.get('id')
    assert response_json.get('name') == api_key_create_request['name']
    assert response_json.get('key').startswith("cue_sk_")
    assert response_json.get('message')

@pytest.mark.asyncio
async def test_create_managed_user_api_key_manager_not_in_ngroup(test_client, test_daac_manager_user, seed_ngroup, seed_user, make_jwt):
    """Test create api key endpoint - daac manager creating managed user key for user not in manager's ngroup."""
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")
    mock_obs_user_id = uuid.uuid4()
    await seed_user(mock_obs_user_id, "test_email@test.com", "test_username_user",
                   "test_user", '2068cc53-1232-4bc7-9647-3e29e6418e21', ngroup_id=ngroup_id2)

    api_key_create_request = {"name":"test_manager_for_observer_key",
                              "key_type":"managed_user",
                              "target_user_id":str(mock_obs_user_id),
                              "expires_in_days":10,
                              "ngroup_id":str(ngroup_id2)}
    
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    assert response.status_code == 400


def test_list_api_keys_endpoint(test_client, test_admin_user, test_daac_observer_user, test_ngroup_id, make_jwt):
    """Test list api key endpoint."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request1 = {"name": "test_key",
                             "key_type": "personal",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "ngroup_id": str(test_ngroup_id)}
    api_key1_response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request1).json()
    api_key_create_request2 = {"name": "test_key",
                             "key_type": "managed_user",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "target_user_id": str(test_daac_observer_user.id),
                             "ngroup_id": str(test_ngroup_id)}
    api_key2_response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request2).json()
    api_key_create_request3 = {"name": "test_key",
                             "key_type": "proxy",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "proxy_user_name": "proxy provider",
                             "ngroup_id": str(test_ngroup_id)}
    api_key3_response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request3).json()

    api_key_ids = sorted([api_key1_response["id"],api_key2_response["id"],api_key3_response["id"]])
    headers["x-active-ngroup-id"] = str(test_ngroup_id)
    list_response = test_client.get("v2/api-keys/", headers=headers)
    list_response_json = list_response.json()
    assert api_key_ids == sorted([api_key["id"] for api_key in list_response_json])


def test_update_api_key_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    """Test update api key endpoint - succuss."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request= {"name": "test_key",
                             "key_type": "personal",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "ngroup_id": str(test_ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    response_json = response.json()
    api_key_id = response_json.get("id")

    api_key_update_request = {"is_active": False}
    response = test_client.patch(f"v2/api-keys/{api_key_id}", headers=headers, json=api_key_update_request)

    response = test_client.get("v2/api-keys/", headers=headers)
    response_json = response.json()

    assert response_json[0]["id"] == api_key_id
    assert response_json[0]["is_active"] == False


def test_update_api_key_endpoint_key_does_not_exist(test_client, test_admin_user, make_jwt):
    """Test update api key endpoint - api key does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_id = str(uuid.uuid4())

    api_key_update_request = {"is_active": False}
    response = test_client.patch(f"v2/api-keys/{api_key_id}", headers=headers, json=api_key_update_request)

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_api_key_endpoint_key_cannot_access(test_client, test_daac_manager_user, seed_ngroup, seed_user, make_jwt):
    """Test update api key endpoint - user lacks privilege."""
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    ngroup_1_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}


    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")

    mock_staff_user_id = uuid.uuid4()
    await seed_user(mock_staff_user_id, "test_email@test.com", "test_username_user",
                    "test_user", "a8b3757b-dcf9-4943-8f64-5adaf17a17fe", ngroup_id=ngroup_id2)

    mock_staff_user_jwt = make_jwt(sub=str(mock_staff_user_id))
    mock_staff_user_headers = {"Authorization": f"Bearer {mock_staff_user_jwt}"}

    api_key_create_request= {"name": "test_key",
                             "key_type": "personal",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "ngroup_id": str(ngroup_id2)}
    
    response = test_client.post("v2/api-keys/", headers=mock_staff_user_headers, json=api_key_create_request)
    api_key_id = response.json().get("id")

    api_key_update_request = {"is_active": False}
    response = test_client.patch(f"v2/api-keys/{api_key_id}", headers=ngroup_1_manager_headers, json=api_key_update_request)

    assert response.status_code == 403

@pytest.mark.asyncio
async def test_record_key_usage_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt, connection_pool):
    """Test record key usage endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request= {"name": "test_key",
                             "key_type": "personal",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "ngroup_id": str(test_ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    response_json = response.json()
    api_key_id = response_json.get("id")
    response = test_client.patch(f"v2/api-keys/{api_key_id}/record-usage", headers=headers)
    assert response.status_code == 204

    async with connection_pool.acquire() as conn:
        last_used_at = await conn.fetchval("SELECT last_used_at FROM api_key WHERE id = $1", api_key_id)
    assert last_used_at.date() == datetime.now().date()

@pytest.mark.asyncio
async def test_revoke_api_key_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt, connection_pool):
    """Test revoke api key endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request= {"name": "test_key",
                             "key_type": "personal",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "ngroup_id": str(test_ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    response_json = response.json()
    api_key_id = response_json.get("id")
    response = test_client.delete(f"v2/api-keys/{api_key_id}", headers=headers)
    assert response.status_code == 204

    async with connection_pool.acquire() as conn:
        revoked_at = await conn.fetchval("SELECT revoked_at FROM api_key WHERE id = $1", api_key_id)
    assert revoked_at.date() == datetime.now().date()

@pytest.mark.asyncio
async def test_revoke_api_key_endpoint_does_not_exist(test_client, test_admin_user, test_ngroup_id, make_jwt, connection_pool):
    """Test revoke api key endpoint - api key does not exist"""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    api_key_id = uuid.uuid4()
    response = test_client.delete(f"v2/api-keys/{api_key_id}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_revoke_api_key_endpoint_permission_error(test_client, test_daac_manager_user, seed_ngroup, seed_user, make_jwt):
    """Test revoke api key endpoint - permission error user trying to revoke key in different ngroup."""
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    ngroup_1_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")

    mock_staff_user_id = uuid.uuid4()
    await seed_user(mock_staff_user_id, "test_email@test.com", "test_username_user",
                    "test_user", "a8b3757b-dcf9-4943-8f64-5adaf17a17fe", ngroup_id=ngroup_id2)

    mock_staff_user_jwt = make_jwt(sub=str(mock_staff_user_id))
    mock_staff_user_headers = {"Authorization": f"Bearer {mock_staff_user_jwt}"}

    api_key_create_request= {"name": "test_key",
                             "key_type": "personal",
                             "scopes":["file:upload"],
                             "expires_in_days": 10,
                             "ngroup_id": str(ngroup_id2)}
    
    response = test_client.post("v2/api-keys/", headers=mock_staff_user_headers, json=api_key_create_request)
    api_key_id = response.json().get("id")

    response = test_client.delete(f"v2/api-keys/{api_key_id}", headers=ngroup_1_manager_headers)
    assert response.status_code == 403