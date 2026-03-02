import pytest
import uuid

def test_create_egress_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=headers, json=egress_create_request)
    response_json = response.json()
    assert response_json.get("id")
    assert response_json.get("ngroup_id") == test_admin_user.active_ngroup_id

def test_create_egress_endpoint_no_active_ngroup_header(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=headers, json=egress_create_request)
    assert response.status_code == 400

def test_list_egresses_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request1 = {"type": "s3", "path": "test_s3_path1", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data/level1"}}
    egress1_response = test_client.post("v2/egress/", headers=headers, json=egress_create_request1).json()
    egress_create_request2 = {"type": "s3", "path": "test_s3_path2", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data/level2"}}
    egress2_response = test_client.post("v2/egress/", headers=headers, json=egress_create_request2).json()
    egress_create_request3 = {"type": "s3", "path": "test_s3_path3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data/level3"}}
    egress3_response = test_client.post("v2/egress/", headers=headers, json=egress_create_request3).json()
    egress_ids = sorted([egress1_response['id'], egress2_response['id'], egress3_response['id']])

    list_egress_response = test_client.get("v2/egress/", headers=headers).json()
    list_egress_ids = [egress["id"] for egress in list_egress_response]
    for egress_id in egress_ids:
        assert egress_id in list_egress_ids


def test_get_egress_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=headers, json=egress_create_request)
    response_json = response.json()
    egress_id = response_json.get("id")

    response = test_client.get(f"v2/egress/{egress_id}", headers=headers)
    response_json = response.json() 
    assert response_json['id'] == egress_id
    assert response_json['type'] == egress_create_request['type']
    assert response_json['path'] == egress_create_request['path']
    assert response_json['config'] == egress_create_request['config']
    assert response_json['ngroup_id'] == test_admin_user.active_ngroup_id

def test_get_egress_endpoint_egress_not_found(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_id = uuid.uuid4() 

    response = test_client.get(f"v2/egress/{egress_id}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_egress_endpoint_egress_no_access(test_client, test_admin_user, test_daac_manager_user, seed_ngroup, connection_pool, make_jwt):
    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    async with connection_pool.acquire() as conn:
        await conn.execute("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2)", *(test_admin_user.id, ngroup2["id"]))

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":str(ngroup2["id"])}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=admin_headers, json=egress_create_request)
    response_json = response.json()
    egress_id = response_json.get("id")

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}
    response = test_client.get(f"v2/egress/{egress_id}", headers=daac_manager_headers)
    assert response.status_code == 400 

def test_get_egress_endpoint_egress_no_active_ngroup_header(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=admin_headers, json=egress_create_request)
    response_json = response.json()

    egress_id = response_json.get("id")
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}
    egress_id = response_json.get("id")

    response = test_client.get(f"v2/egress/{egress_id}", headers=daac_manager_headers)
    assert response.status_code == 400 

def test_update_egress_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=headers, json=egress_create_request)
    response_json = response.json()
    egress_id = response_json.get("id")

    egress_update_request = {"type":"cumulus", "path":"new_path", "config":{"queue":"forwarding-queue", "bucket":"destination_bucket"}}
    response = test_client.patch(f"v2/egress/{egress_id}", headers=headers, json=egress_update_request)
    response_json = response.json() 
    assert response_json['id'] == egress_id
    assert response_json['type'] == egress_update_request["type"]
    assert response_json['path'] == egress_update_request["path"]
    assert response_json['config'] == egress_update_request["config"]

def test_update_egress_endpoint_egress_not_found(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_id = uuid.uuid4() 

    egress_update_request = {"type":"cumulus", "path":"new_path", "config":{"queue":"forwarding-queue", "bucket":"destination_bucket"}}
    response = test_client.patch(f"v2/egress/{egress_id}", headers=headers, json=egress_update_request)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_egress_endpoint_egress_no_access(test_client, test_admin_user, test_daac_manager_user, seed_ngroup, connection_pool, make_jwt):
    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    async with connection_pool.acquire() as conn:
        await conn.execute("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2)", *(test_admin_user.id, ngroup2["id"]))

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":str(ngroup2["id"])}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=admin_headers, json=egress_create_request)
    response_json = response.json()
    egress_id = response_json.get("id")

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}
    egress_update_request = {"type":"cumulus", "path":"new_path", "config":{"queue":"forwarding-queue", "bucket":"destination_bucket"}}
    response = test_client.patch(f"v2/egress/{egress_id}", headers=daac_manager_headers, json=egress_update_request)
    assert response.status_code == 400 

def test_update_egress_endpoint_egress_no_active_ngroup_header(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=admin_headers, json=egress_create_request)
    response_json = response.json()

    egress_id = response_json.get("id")
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    egress_update_request = {"type":"cumulus", "path":"new_path", "config":{"queue":"forwarding-queue", "bucket":"destination_bucket"}}
    response = test_client.patch(f"v2/egress/{egress_id}", headers=daac_manager_headers, json=egress_update_request)
    assert response.status_code == 400 


def test_delete_egress_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=headers, json=egress_create_request)
    response_json = response.json()
    egress_id = response_json["id"]

    response = test_client.get(f"v2/egress/{egress_id}", headers=headers)
    response_json = response.json() 
    assert response_json['id'] == egress_id

    response = test_client.delete(f"v2/egress/{egress_id}", headers=headers)
    assert response.status_code == 204

    response = test_client.get(f"v2/egress/{egress_id}", headers=headers)
    response_json = response.json() 
    assert response.status_code == 404

def test_delete_egress_endpoint_egress_not_found(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_id = uuid.uuid4() 

    egress_update_request = {"type":"cumulus", "path":"new_path", "config":{"queue":"forwarding-queue", "bucket":"destination_bucket"}}
    response = test_client.patch(f"v2/egress/{egress_id}", headers=headers, json=egress_update_request)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_egress_endpoint_egress_no_access(test_client, test_admin_user, test_daac_manager_user, seed_ngroup, connection_pool, make_jwt):
    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    async with connection_pool.acquire() as conn:
        await conn.execute("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2)", *(test_admin_user.id, ngroup2["id"]))

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":str(ngroup2["id"])}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=admin_headers, json=egress_create_request)
    response_json = response.json()
    egress_id = response_json.get("id")

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}
    response = test_client.delete(f"v2/egress/{egress_id}", headers=daac_manager_headers)
    assert response.status_code == 400 

def test_delete_egress_endpoint_egress_no_active_ngroup_header(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_create_request = {"type": "s3", "path": "test_s3", 
                             "config": {"bucket":"destination_bucket","destination_path":"/data"}}
    response = test_client.post("v2/egress/", headers=admin_headers, json=egress_create_request)
    response_json = response.json()

    egress_id = response_json.get("id")
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    response = test_client.delete(f"v2/egress/{egress_id}", headers=daac_manager_headers)
    assert response.status_code == 400 

def test_delete_egress_endpoint(test_client, test_collection, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    egress_id = test_collection["egress_id"]

    response = test_client.delete(f"v2/egress/{egress_id}", headers=headers)
    assert response.status_code == 409