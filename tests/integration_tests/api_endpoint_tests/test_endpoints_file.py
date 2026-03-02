import pytest
import uuid 
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_list_files_endpoint(test_client, test_admin_user, seed_file, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    file_ids = sorted([uuid.uuid4() for _ in range(8)])
    await seed_file(file_ids[0],"file1", 'application/octet-stream', test_admin_user.id, 1024, status="unscanned")
    await seed_file(file_ids[1],"file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    await seed_file(file_ids[2],"file3", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[3],"file4", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[4],"file6", 'application/octet-stream', test_admin_user.id, 1024, status="scan_failed")
    await seed_file(file_ids[5],"file7", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[6],"file8", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[7],"file9", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    params = {
               "page":1,
               "page_size":50,
               "start_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
               "end_date":datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    }
    response = test_client.get("/v2/files/", headers=headers, params=params)
    response_json = response.json()

    list_files_ids = sorted([uuid.UUID(file["id"]) for file in response_json["items"]])
    assert isinstance(response_json["items"], list)
    assert list_files_ids == file_ids
    assert response_json["total"] == 8
    assert response_json["page"] == 1
    assert response_json["page_size"] == 50

@pytest.mark.asyncio
async def test_list_files_by_api_key_endpoint(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    scopes=["file:upload", "file:read"]
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request = {"name": "test_key", "key_type": "personal", "scopes": scopes, "expires_in_days": 10, "ngroup_id": str(test_ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    api_key = response.json()["key"]

    file_ids = sorted([uuid.uuid4() for _ in range(8)])
    await seed_file(file_ids[0],"file1", 'application/octet-stream', test_admin_user.id, 1024, status="unscanned")
    await seed_file(file_ids[1],"file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    await seed_file(file_ids[2],"file3", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[3],"file4", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[4],"file6", 'application/octet-stream', test_admin_user.id, 1024, status="scan_failed")
    await seed_file(file_ids[5],"file7", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[6],"file8", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[7],"file9", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")

    file_list_request = {
        "apiKey": api_key,
        "status": "distributed",
        "page": 1,
        "page_size": 50,
        "start_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "end_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    }
    response = test_client.post("v2/files/list", headers=headers, json=file_list_request)
    response_json = response.json()
  
    assert response_json["items"] and len(response_json["items"]) > 0
    list_file_ids = sorted([uuid.UUID(file["id"]) for file in response_json["items"]])
    assert list_file_ids == file_ids[5:8]

@pytest.mark.asyncio
async def test_list_files_by_api_key_endpoint_api_scope_error(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    scopes=["file:upload"]
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request = {"name": "test_key", "key_type": "personal", "scopes": scopes, "expires_in_days": 10, "ngroup_id": str(test_ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    api_key = response.json()["key"]

    file_ids = sorted([uuid.uuid4() for _ in range(8)])
    await seed_file(file_ids[0],"file1", 'application/octet-stream', test_admin_user.id, 1024, status="unscanned")
    await seed_file(file_ids[1],"file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    await seed_file(file_ids[2],"file3", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[3],"file4", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[4],"file6", 'application/octet-stream', test_admin_user.id, 1024, status="scan_failed")
    await seed_file(file_ids[5],"file7", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[6],"file8", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[7],"file9", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")

    file_list_request = {
        "apiKey": api_key,
        "status": "distributed",
        "page": 1,
        "page_size": 50,
        "start_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "end_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    }
    response = test_client.post("v2/files/list", headers=headers, json=file_list_request)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_list_files_by_api_key_endpoint_file_access_error(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    scopes=["file:upload", "file:read"]
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key_create_request = {"name": "test_key", "key_type": "personal", "scopes": scopes, "expires_in_days": 10, "ngroup_id": str(test_ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    api_key = response.json()["key"]

    file_ids = sorted([uuid.uuid4() for _ in range(8)])
    await seed_file(file_ids[0],"file1", 'application/octet-stream', test_admin_user.id, 1024, status="unscanned")
    await seed_file(file_ids[1],"file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    await seed_file(file_ids[2],"file3", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[3],"file4", 'application/octet-stream', test_admin_user.id, 1024, status="infected")
    await seed_file(file_ids[4],"file6", 'application/octet-stream', test_admin_user.id, 1024, status="scan_failed")
    await seed_file(file_ids[5],"file7", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[6],"file8", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_ids[7],"file9", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")

    file_list_request = {
        "apiKey": api_key,
        "status": "distributed",
        "page": 1,
        "page_size": 50,
        "file_id": str(uuid.uuid4())
    }
    response = test_client.post("v2/files/list", headers=headers, json=file_list_request)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_find_files_by_name_endpoint(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    file_id = uuid.uuid4()
    await seed_file(file_id,"file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    params = { "name": "file1" }

    response = test_client.get("/v2/files/find", headers=headers, params=params)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json[0]["id"] == str(file_id) 
    assert response_json[0]["name"] ==  "file1"


@pytest.mark.asyncio
async def test_get_file_endpoint(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    file_id = uuid.uuid4()
    await seed_file(file_id,"file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    response = test_client.get(f"/v2/files/{file_id}", headers=headers)
    response_json = response.json()

    assert response.status_code == 200
    assert response_json["id"] == str(file_id) 
    assert response_json["name"] ==  "file1"

@pytest.mark.asyncio
async def test_get_file_endpoint_not_found(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    file_id = uuid.uuid4()
    response = test_client.get(f"/v2/files/{file_id}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_file_endpoint_no_access(test_client, test_admin_user, test_daac_manager_user, test_ngroup_id, seed_ngroup, seed_egress, seed_provider, seed_collection, seed_file, make_jwt, mock_boto3_client):
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}", "x-active-ngroup-id":test_daac_manager_user.active_ngroup_id}

    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])
    collection2 = await seed_collection("test_collection2", True, egress_id=egress2["id"], provider_id=provider2["id"], ngroup_id=ngroup2["id"] )
    file_id = uuid.uuid4()
    await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", collection_id=collection2["id"])

    response = test_client.get(f"/v2/files/{file_id}", headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_update_file_endpoint(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}

    file_id = uuid.uuid4()
    await seed_file(file_id,"file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")

    file_update_request = {
        "name" : "new_file1_name",
        "collection_path": "/new/file/path/"
    }

    response = test_client.patch(f"/v2/files/{file_id}", headers=headers, json=file_update_request)
    response_json = response.json()

    assert response.status_code == 200
    assert response_json["id"] == str(file_id) 
    assert response_json["name"] == file_update_request["name"]
    assert response_json["collection_path"] == file_update_request["collection_path"]

@pytest.mark.asyncio
async def test_update_file_endpoint_not_found(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}

    file_id = uuid.uuid4()

    file_update_request = {
        "name" : "new_file1_name",
        "collection_path": "/new/file/path/"
    }

    response = test_client.patch(f"/v2/files/{file_id}", headers=headers, json=file_update_request)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_file_endpoint_empty_update(test_client, test_admin_user, test_ngroup_id, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}

    file_id = uuid.uuid4()
    await seed_file(file_id,"file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")

    file_update_request = {}

    response = test_client.patch(f"/v2/files/{file_id}", headers=headers, json=file_update_request)

    assert response.status_code == 400

@pytest.mark.asyncio
async def test_update_file_endpoint_no_access(test_client, test_admin_user, test_daac_manager_user, test_ngroup_id, seed_ngroup, seed_egress, seed_provider, seed_collection, seed_file, make_jwt, mock_boto3_client):
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}", "x-active-ngroup-id":test_daac_manager_user.active_ngroup_id}

    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])
    collection2 = await seed_collection("test_collection2", True, egress_id=egress2["id"], provider_id=provider2["id"], ngroup_id=ngroup2["id"] )
    file_id = uuid.uuid4()
    await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", collection_id=collection2["id"])

    file_update_request = {
        "name" : "new_file1_name",
        "collection_path": "/new/file/path/"
    }

    response = test_client.patch(f"/v2/files/{file_id}", headers=headers, json=file_update_request)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_delete_file_endpoint(test_client, test_admin_user, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    file_id = uuid.uuid4()
    await seed_file(file_id,"file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")

    response = test_client.delete(f"/v2/files/{file_id}", headers=headers)

    assert response.status_code == 204

    response = test_client.get(f"/v2/files/{file_id}", headers=headers)

    assert response.status_code ==  404

@pytest.mark.asyncio
async def test_delete_file_endpoint_not_found(test_client, test_admin_user, seed_file, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":test_admin_user.active_ngroup_id}
    file_id = uuid.uuid4()

    response = test_client.delete(f"/v2/files/{file_id}", headers=headers)

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_file_endpoint_no_access(test_client, test_admin_user, test_daac_manager_user, test_ngroup_id, seed_ngroup, seed_egress, seed_provider, seed_collection, seed_file, make_jwt, mock_boto3_client):
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}", "x-active-ngroup-id":test_daac_manager_user.active_ngroup_id}

    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])
    collection2 = await seed_collection("test_collection2", True, egress_id=egress2["id"], provider_id=provider2["id"], ngroup_id=ngroup2["id"] )
    file_id = uuid.uuid4()
    await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", collection_id=collection2["id"])

    response = test_client.delete(f"/v2/files/{file_id}", headers=headers)
    assert response.status_code == 403