import uuid


def test_create_role_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    response_json = response.json()

    assert response_json.get("id")
    assert response_json.get("short_name") == role_create_request["short_name"]
    assert response_json.get("long_name") == role_create_request["long_name"]

def test_create_role_endpoint_duplicate(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    assert response.status_code == 201

    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    assert response.status_code == 400


def test_list_roles_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    role_create_request1 = {"short_name":"new_role 1", "long_name":"New Role 1"}
    role_response1 = test_client.post("/v2/roles/", headers=headers, json=role_create_request1).json()

    role_create_request2 = {"short_name":"new_role2", "long_name":"New Role 2"}
    role_response2 = test_client.post("/v2/roles/", headers=headers, json=role_create_request2).json()

    role_create_request3 = {"short_name":"new_role3", "long_name":"New Role 3"}
    role_response3 = test_client.post("/v2/roles/", headers=headers, json=role_create_request3).json()

    role_ids = [role_response1["id"],role_response2["id"],role_response3["id"]]

    list_response_json = test_client.get("/v2/roles/", headers=headers).json()
    assert role_ids[0] in [role["id"] for role in list_response_json] 
    assert role_ids[1] in [role["id"] for role in list_response_json] 
    assert role_ids[2] in [role["id"] for role in list_response_json] 

def test_lookup_role_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    assert response.status_code == 201

    response = test_client.get("/v2/roles/find", params={"short_name":role_create_request["short_name"]}, headers=headers)
    response_json1 = response.json()

    assert response_json1.get("short_name") == role_create_request["short_name"]
    assert response_json1.get("long_name") == role_create_request["long_name"]

    response = test_client.get("/v2/roles/find", params={"long_name":role_create_request["long_name"]}, headers=headers)
    response_json2 = response.json()

    assert response_json2.get("short_name") == role_create_request["short_name"]
    assert response_json2.get("long_name") == role_create_request["long_name"]

    assert response_json1 == response_json2

def test_lookup_role_endpoint_not_found(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    assert response.status_code == 201

    response = test_client.get("/v2/roles/find", params={"short_name":"bad_name"}, headers=headers)
    assert response.status_code == 404

    response = test_client.get("/v2/roles/find", params={"long_name":"bad_name"}, headers=headers)
    assert response.status_code == 404

def test_lookup_role_endpoint_empty_param(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    assert response.status_code == 201

    response = test_client.get("/v2/roles/find", params={}, headers=headers)
    assert response.status_code == 400

def test_get_role_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    assert response.status_code == 201
    response_json = response.json()
    role_id = response_json.get("id")

    response = test_client.get(f"/v2/roles/{role_id}", headers=headers)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json.get("short_name") == role_create_request["short_name"]
    assert response_json.get("long_name") == role_create_request["long_name"]

def test_get_role_endpoint_not_found(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_id = uuid.uuid4()

    response = test_client.get(f"/v2/roles/{role_id}", headers=headers)
    assert response.status_code == 404

def test_update_role_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    response_json = response.json()
    role_id = response_json.get("id")
    
    update_role_request = {"short_name":"old_new_role", "long_name":"Old New Role"}
    response = test_client.patch(f"/v2/roles/{role_id}", headers=headers, json=update_role_request)
    response_json = response.json()
    assert response_json.get("id") == role_id
    assert response_json.get("short_name") == update_role_request.get("short_name")
    assert response_json.get("long_name") == update_role_request.get("long_name")

def test_update_role_endpoint_not_found(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_id = uuid.uuid4()
    
    update_role_request = {"short_name":"old_new_role", "long_name":"Old New Role"}
    response = test_client.patch(f"/v2/roles/{role_id}", headers=headers, json=update_role_request)
    assert response.status_code == 404

def test_update_role_endpoint_empty_update(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    response_json = response.json()
    role_id = response_json.get("id")
    
    update_role_request = {}
    response = test_client.patch(f"/v2/roles/{role_id}", headers=headers, json=update_role_request)
    assert response.status_code == 400

def test_update_role_endpoint_no_access(test_client, test_admin_user, test_daac_staff_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=admin_headers, json=role_create_request)
    response_json = response.json()
    role_id = response_json.get("id")

    test_daac_staff_user_jwt = make_jwt(sub=str(test_daac_staff_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_staff_user_jwt}"}
    
    update_role_request = {"short_name":"old_new_role", "long_name":"Old New Role"}
    response = test_client.patch(f"/v2/roles/{role_id}", headers=daac_manager_headers, json=update_role_request)
    assert response.status_code == 403

def test_delete_role_endpoint(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=headers, json=role_create_request)
    response_json = response.json()
    role_id = response_json.get("id")
    response = test_client.get("/v2/roles/find", params={"short_name":role_create_request["short_name"]}, headers=headers)
    assert response.status_code == 200

    response = test_client.delete(f"/v2/roles/{role_id}", headers=headers)
    assert response.status_code == 204

    response = test_client.get("/v2/roles/find", params={"short_name":role_create_request["short_name"]}, headers=headers)
    assert response.status_code == 404 

def test_delete_role_endpoint_not_found(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_id = uuid.uuid4()

    response = test_client.delete(f"/v2/roles/{role_id}", headers=headers)
    assert response.status_code == 404

def test_delete_role_endpoint_no_access(test_client, test_admin_user, test_daac_staff_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    role_create_request = {"short_name":"new_role", "long_name":"New Role"}
    response = test_client.post("/v2/roles/", headers=admin_headers, json=role_create_request)
    response_json = response.json()
    role_id = response_json.get("id")

    test_daac_staff_user_jwt = make_jwt(sub=str(test_daac_staff_user.id))
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_staff_user_jwt}"}
    
    response = test_client.delete(f"/v2/roles/{role_id}", headers=daac_manager_headers)
    assert response.status_code == 403