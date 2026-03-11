import pytest
import uuid

def test_create_collection_endpoint(test_client, test_admin_user, test_provider, test_egress, make_jwt):
    """Test create collection endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}
    response = test_client.post("/v2/collections/", headers=headers, json=create_collection_request)
    response_json = response.json()
    assert response_json.get("id")
    assert response_json.get("provider_id") == str(test_provider["id"])
    assert response_json.get("egress_id") == str(test_egress["id"])

@pytest.mark.asyncio
async def test_create_collection_endpoint_bad_requests(test_client, test_admin_user, test_daac_manager_user,
                                                       seed_provider, seed_egress, seed_ngroup,
                                                       test_provider, test_egress, make_jwt):
    """Test create collection endpoint - provider/egress belong to different ngroup."""
    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id),
                                    active_ngroup_id=test_daac_manager_user.active_ngroup_id,
                                    roles=test_daac_manager_user.roles,
                                    ngroups=test_daac_manager_user.ngroups)
    headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}
    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])
    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(provider2['id']),
                                 "egress_id": str(test_egress['id'])}
    response = test_client.post("/v2/collections/", headers=headers, json=create_collection_request)
    assert response.status_code == 400

    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(egress2['id'])}
    response = test_client.post("/v2/collections/", headers=headers, json=create_collection_request)
    assert response.status_code == 400

def test_list_collection_endpoint(test_client, test_admin_user, test_provider, test_egress, make_jwt):
    """Test list collection endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    headers = {"Authorization": f"Bearer {test_admin_user_jwt}",
               "x-active-ngroup-id": test_admin_user.active_ngroup_id}

    create_collection_request1 = {"short_name":"new_test_collection1",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}

    collection_response1 = test_client.post("/v2/collections/", headers=headers, json=create_collection_request1).json()
    create_collection_request2 = {"short_name":"new_test_collection2",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}

    collection_response2 = test_client.post("/v2/collections/", headers=headers, json=create_collection_request2).json()
    create_collection_request3 = {"short_name":"new_test_collection3",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}

    collection_response3 = test_client.post("/v2/collections/", headers=headers, json=create_collection_request3).json()

    collection_ids = sorted([collection_response1["id"],collection_response2["id"],collection_response3["id"]])
    list_response_json = test_client.get("/v2/collections/", headers=headers).json()
    list_collection_ids = [ collection["id"] for collection in list_response_json]
    for collection_id in collection_ids:
        assert collection_id in list_collection_ids

def test_list_collection_endpoint_no_active_ngroup(test_client, test_admin_user, test_daac_manager_user,
                                                   test_provider, test_egress, make_jwt):
    """Test list collection endpoint - missing x-active-ngroup-id header."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}",
               "x-active-ngroup-id": test_admin_user.active_ngroup_id}

    create_collection_request1 = {"short_name":"new_test_collection1",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}
    test_client.post("/v2/collections/", headers=admin_headers, json=create_collection_request1).json()

    create_collection_request2 = {"short_name":"new_test_collection2",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}
    test_client.post("/v2/collections/", headers=admin_headers, json=create_collection_request2).json()

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id))
    headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}
    response = test_client.get("/v2/collections/", headers=headers)
    assert response.status_code == 400

def test_get_collection_endpoint(test_client, test_admin_user, test_provider, test_egress, make_jwt):
    """Test get collection endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}

    response = test_client.post("/v2/collections/", headers=headers, json=create_collection_request)
    response_json = response.json()

    collection_id = response_json.get("id")

    response = test_client.get(f"/v2/collections/{collection_id}", headers=headers)
    response_json = response.json()
    assert collection_id == response_json["id"]
    assert create_collection_request["short_name"] == response_json["short_name"]
    assert create_collection_request["active"] == response_json["active"]
    assert create_collection_request["provider_id"] == response_json["provider_id"]
    assert create_collection_request["egress_id"] == response_json["egress_id"]

def test_get_collection_endpoint_does_not_exist(test_client, test_admin_user, make_jwt):
    """Test get collection endpoint - collection does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    collection_id = str(uuid.uuid4())

    response = test_client.get(f"/v2/collections/{collection_id}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_collection_endpoint_non_access(test_client, test_admin_user, test_daac_manager_user, 
                                                  seed_provider, seed_egress, seed_ngroup, make_jwt):
    """Test get collection endpoint - user and collection in different ngroups."""
    ngroup2_id = uuid.uuid4()
    ngroup2 = await seed_ngroup(ngroup2_id, "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=str(ngroup2_id),
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(provider2['id']),
                                 "egress_id": str(egress2['id'])}
    response = test_client.post("/v2/collections/", headers=admin_headers, json=create_collection_request)
    response_json = response.json()
    collection_id = response_json.get("id")
    assert response.status_code == 201

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id),
                                    active_ngroup_id=test_daac_manager_user.active_ngroup_id,
                                    roles=test_daac_manager_user.roles,
                                    ngroups=test_daac_manager_user.ngroups)
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    response = test_client.get(f"/v2/collections/{collection_id}", headers=daac_manager_headers)
    assert response.status_code == 500

def test_update_collection_endpoint(test_client, test_admin_user, test_provider, test_egress, make_jwt):
    """Test update collection endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}
    response = test_client.post("/v2/collections/", headers=headers, json=create_collection_request)
    response_json = response.json()
    collection_id = response_json.get("id")

    update_collection_request = {"short_name":"test_new_collection", "active":False}

    response = test_client.patch(f"/v2/collections/{collection_id}", headers=headers, json=update_collection_request)
    response_json = response.json()
    assert collection_id == response_json["id"]
    assert update_collection_request["short_name"] == response_json["short_name"]
    assert update_collection_request["active"] == response_json["active"]

def test_update_collection_endpoint_not_found(test_client, test_admin_user, make_jwt):
    """Test update collection endpoint - collection does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    collection_id = uuid.uuid4()

    update_collection_request = {"short_name":"test_new_collection", "active":False}

    response = test_client.patch(f"/v2/collections/{collection_id}", headers=headers, json=update_collection_request)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_collection_endpoint_non_access(test_client, test_admin_user, test_daac_manager_user,
                                                     seed_provider, seed_egress, seed_ngroup, make_jwt):
    """Test update collection endpoint - user and collection in different ngroups."""
    ngroup2_id = uuid.uuid4()
    ngroup2 = await seed_ngroup(ngroup2_id, "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=str(ngroup2_id),
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(provider2['id']),
                                 "egress_id": str(egress2['id'])}
    response = test_client.post("/v2/collections/", headers=admin_headers, json=create_collection_request)
    response_json = response.json()
    collection_id = response_json.get("id")

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id),
                                    active_ngroup_id=test_daac_manager_user.active_ngroup_id,
                                    roles=test_daac_manager_user.roles,
                                    ngroups=test_daac_manager_user.ngroups)
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    update_collection_request = {"short_name":"test_new_collection", "active":False}

    response = test_client.patch(f"/v2/collections/{collection_id}", headers=daac_manager_headers, json=update_collection_request)
    assert response.status_code == 403

def test_delete_collection_endpoint(test_client, test_admin_user, test_provider, test_egress, make_jwt):
    """Test delete collection endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(test_provider['id']),
                                 "egress_id": str(test_egress['id'])}
    response = test_client.post("/v2/collections/", headers=headers, json=create_collection_request)
    response_json = response.json()
    collection_id = response_json.get("id")

    response = test_client.get(f"/v2/collections/{collection_id}", headers=headers)
    assert response.status_code == 200

    response = test_client.delete(f"/v2/collections/{collection_id}", headers=headers)
    assert response.status_code == 204

    response = test_client.get(f"/v2/collections/{collection_id}", headers=headers)
    assert response.status_code == 404

def test_delete_collection_endpoint_not_found(test_client, test_admin_user, make_jwt):
    """Test delete collection endpoint - collection does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=test_admin_user.active_ngroup_id,
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    collection_id = uuid.uuid4()

    response = test_client.delete(f"/v2/collections/{collection_id}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_collection_endpoint_non_access(test_client, test_admin_user, test_daac_manager_user,
                                                     seed_provider, seed_egress, seed_ngroup, make_jwt):
    """Test delete collection endpoint - user and collection in different ngroups."""
    ngroup2_id = uuid.uuid4()
    ngroup2 = await seed_ngroup(ngroup2_id, "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id),
                                   active_ngroup_id=str(ngroup2_id),
                                   roles=test_admin_user.roles,
                                   ngroups=test_admin_user.ngroups)

    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    create_collection_request = {"short_name":"new_test_collection",
                                 "active":True,
                                 "provider_id": str(provider2['id']),
                                 "egress_id": str(egress2['id'])}
    response = test_client.post("/v2/collections/", headers=admin_headers, json=create_collection_request)
    response_json = response.json()
    collection_id = response_json.get("id")

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id),
                                    active_ngroup_id=test_daac_manager_user.active_ngroup_id,
                                    roles=test_daac_manager_user.roles,
                                    ngroups=test_daac_manager_user.ngroups)
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    response = test_client.delete(f"/v2/collections/{collection_id}", headers=daac_manager_headers)
    assert response.status_code == 500
