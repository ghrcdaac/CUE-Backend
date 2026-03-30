import uuid


def test_create_ngroup_endpoint(test_client, test_admin_user, make_jwt):
    """Test create ngroup endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request) 
    response_json = response.json()
    
    assert response_json.get("id")
    assert create_ngroup_request["short_name"] == response_json.get("short_name")
    assert create_ngroup_request["long_name"] == response_json.get("long_name")

def test_create_ngroup_endpoint_duplicate(test_client, test_admin_user, make_jwt):
    """Test create ngroup endpoint - duplicate ngroup"""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request) 
    assert response.status_code == 201

    response = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request) 
    assert response.status_code == 400


def test_list_ngroups_for_application_form(test_client, test_admin_user, make_jwt):
    """Test list ngroups for application form."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    create_ngroup_request1 = {"short_name":"new_ngroup1", "long_name":"New Ngroup1"}
    ngroup_response1 = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request1).json()

    create_ngroup_request2 = {"short_name":"new_ngroup2", "long_name":"New Ngroup2"}
    ngroup_response2 = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request2).json()

    create_ngroup_request3 = {"short_name":"new_ngroup3", "long_name":"New Ngroup3"}
    ngroup_response3 = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request3).json()

    ngroup_ids = [ngroup_response1["id"], ngroup_response2["id"], ngroup_response3["id"]]
    list_response_json = test_client.get("v2/ngroups/for-application-form", headers=headers).json()
    assert ngroup_ids[0] in [ngroup["id"] for ngroup in list_response_json]
    assert ngroup_ids[1] in [ngroup["id"] for ngroup in list_response_json]
    assert ngroup_ids[2] in [ngroup["id"] for ngroup in list_response_json]


def test_list_ngroups_endpoint(test_client, test_admin_user, make_jwt):
    """Test list ngroups endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}

    create_ngroup_request1 = {"short_name":"new_ngroup1", "long_name":"New Ngroup1"}
    ngroup_response1 = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request1).json()

    create_ngroup_request2 = {"short_name":"new_ngroup2", "long_name":"New Ngroup2"}
    ngroup_response2 = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request2).json()

    create_ngroup_request3 = {"short_name":"new_ngroup3", "long_name":"New Ngroup3"}
    ngroup_response3 = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request3).json()

    ngroup_ids = [ngroup_response1["id"], ngroup_response2["id"], ngroup_response3["id"]]
    list_response_json = test_client.get("v2/ngroups/", headers=headers).json()
    assert ngroup_ids[0] in [ngroup["id"] for ngroup in list_response_json]
    assert ngroup_ids[1] in [ngroup["id"] for ngroup in list_response_json]
    assert ngroup_ids[2] in [ngroup["id"] for ngroup in list_response_json]

def test_get_ngroup_endpoint(test_client, test_admin_user, make_jwt):
    """Test get ngroup endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request) 
    response_json = response.json()
    ngroup_id = response_json.get("id")

    response = test_client.get(f"v2/ngroups/{ngroup_id}", headers=headers)
    response_json = response.json()

    assert response_json.get("id") == ngroup_id
    assert create_ngroup_request["short_name"] == response_json.get("short_name")
    assert create_ngroup_request["long_name"] == response_json.get("long_name")

def test_get_ngroup_endpoint_not_found(test_client, test_admin_user, make_jwt):
    """Test get ngroup endpoint - ngroup does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    ngroup_id = uuid.uuid4()

    response = test_client.get(f"v2/ngroups/{ngroup_id}", headers=headers)

    assert response.status_code == 404

def test_update_ngroup_endpoint(test_client, test_admin_user, make_jwt):
    """Test update ngroup endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request) 
    response_json = response.json()
    ngroup_id = response_json.get("id")
    update_ngroup_request = {"short_name":"change_name_ngroup", "long_name":"Change Name Ngroup"}

    response = test_client.patch(f"v2/ngroups/{ngroup_id}", headers=headers, json=update_ngroup_request) 
    response_json = response.json()

    assert response_json["id"] == ngroup_id
    assert update_ngroup_request["short_name"] == response_json["short_name"]
    assert update_ngroup_request["long_name"] == response_json["long_name"]

def test_update_ngroup_endpoint_not_found(test_client, test_admin_user, make_jwt):
    """Test update ngroup endpoint - ngroup not found."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    ngroup_id = uuid.uuid4() 
    update_ngroup_request = {"short_name":"change_name_ngroup", "long_name":"Change Name Ngroup"}

    response = test_client.patch(f"v2/ngroups/{ngroup_id}", headers=headers, json=update_ngroup_request) 

    assert response.status_code == 404

def test_update_ngroup_endpoint_empty_update(test_client, test_admin_user, make_jwt):
    """Test update ngroup endpoint - empty update."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request) 
    response_json = response.json()
    ngroup_id = response_json.get("id")
    update_ngroup_request = {}

    response = test_client.patch(f"v2/ngroups/{ngroup_id}", headers=headers, json=update_ngroup_request) 

    assert response.status_code == 400

def test_update_ngroup_endpoint_no_access(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    """Test update ngroup endpoint - non-admin trying to update."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=admin_headers, json=create_ngroup_request) 
    response_json = response.json()
    ngroup_id = response_json.get("id")
    update_ngroup_request = {"short_name":"change_name_ngroup", "long_name":"Change Name Ngroup"}

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}

    response = test_client.patch(f"v2/ngroups/{ngroup_id}", headers=daac_manager_headers, json=update_ngroup_request) 

    assert response.status_code == 403

def test_delete_ngroup_endpoint(test_client, test_admin_user, make_jwt):
    """Test delete ngroup endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=headers, json=create_ngroup_request) 
    response_json = response.json()
    ngroup_id = response_json.get("id")

    response = test_client.get(f"v2/ngroups/{ngroup_id}", headers=headers) 
    assert response.status_code == 200

    response = test_client.delete(f"v2/ngroups/{ngroup_id}", headers=headers) 
    assert response.status_code == 204

    response = test_client.get(f"v2/ngroups/{ngroup_id}", headers=headers) 
    assert response.status_code == 404

def test_delete_ngroup_endpoint_not_found(test_client, test_admin_user, make_jwt):
    """Test delete ngroup endpoint - ngroup does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    ngroup_id = uuid.uuid4()

    response = test_client.get(f"v2/ngroups/{ngroup_id}", headers=headers) 
    assert response.status_code == 404


def test_delete_ngroup_endpoint_no_access(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    """Test delete ngroup endpoint - non-admin trying to delete"""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_ngroup_request = {"short_name":"new_ngroup", "long_name":"New Ngroup"}
    response = test_client.post("v2/ngroups/", headers=admin_headers, json=create_ngroup_request) 
    response_json = response.json()
    ngroup_id = response_json.get("id")

    test_daac_manager_user_jwt = make_jwt(sub=str(test_daac_manager_user.id), roles=test_daac_manager_user.roles, ngroups=test_daac_manager_user.ngroups)
    daac_manager_headers = {"Authorization": f"Bearer {test_daac_manager_user_jwt}"}
    response = test_client.delete(f"v2/ngroups/{ngroup_id}", headers=daac_manager_headers) 
    assert response.status_code == 403 
