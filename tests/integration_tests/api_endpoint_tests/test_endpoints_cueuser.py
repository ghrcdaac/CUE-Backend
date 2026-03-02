import pytest
import uuid

def test_get_my_profile(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get("v2/cueusers/me", headers=headers)
    response_json = response.json()
    assert response_json.get('id') == str(test_admin_user.id)
    assert response_json.get('roles') == test_admin_user.roles

def test_get_my_profile_not_found(test_client, test_admin_user, make_jwt):
    user_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {user_jwt}"}
    response = test_client.get("v2/cueusers/me", headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_list_users_endpoint(test_client, test_admin_user, test_daac_manager_user, test_daac_staff_user, test_daac_observer_user, test_provider_user, test_ngroup_id, make_jwt, seed_user):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "active_ngroup_id":str(test_ngroup_id)}
    response = test_client.get("v2/cueusers/", headers=headers)
    response_json = response.json()
    ids = [user['id'] for user in response_json]
    assert str(test_admin_user.id) in ids
    assert str(test_daac_manager_user.id) in ids
    assert str(test_daac_staff_user.id) in ids
    assert str(test_daac_observer_user.id) in ids
    assert str(test_provider_user.id) in ids

def test_create_users_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    user_id = uuid.uuid4()
    create_user_request = {"user_id": str(user_id),
                           "email": "new_user@test.com",
                           "name": "new user",
                           "cueusername":"new_user",
                           "role_id":"2068cc53-1232-4bc7-9647-3e29e6418e21",
                           "ngroup_ids":[str(test_ngroup_id)],
                           "edpub_id":None}
    response = test_client.post("v2/cueusers/", headers=headers, json=create_user_request)
    response_json = response.json()
    assert str(user_id) == response_json.get('id')
    assert "new_user" == response_json.get('cueusername')
    assert response_json.get('registered')

def test_create_users_endpoint_user_already_exists(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    user_id = uuid.uuid4()
    create_user_request = {"user_id": str(user_id),
                           "email": "new_user@test.com",
                           "name": "new user",
                           "cueusername":"new_user",
                           "role_id":"2068cc53-1232-4bc7-9647-3e29e6418e21",
                           "ngroup_ids":[str(test_ngroup_id)],
                           "edpub_id":None}
    response = test_client.post("v2/cueusers/", headers=headers, json=create_user_request)
    assert response.status_code == 201

    response = test_client.post("v2/cueusers/", headers=headers, json=create_user_request)
    assert response.status_code == 409

def test_create_users_endpoint_user_no_provider_no_ngroup(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    user_id = uuid.uuid4()
    create_user_request = {"user_id": str(user_id),
                           "email": "new_user@test.com",
                           "name": "new user",
                           "cueusername":"new_user",
                           "role_id":"2068cc53-1232-4bc7-9647-3e29e6418e21",
                           "ngroup_ids": [],
                           "edpub_id":None}
    response = test_client.post("v2/cueusers/", headers=headers, json=create_user_request)
    assert response.status_code == 400 

def test_find_user_endpoint(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    criteria_email = {"email": test_daac_manager_user.email}
    response = test_client.get("v2/cueusers/find", headers=headers, params=criteria_email)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_daac_manager_user.id)

    criteria_cueusername = {"cueusername": test_daac_manager_user.cueusername}
    response = test_client.get("v2/cueusers/find", headers=headers, params=criteria_cueusername)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_daac_manager_user.id)

    criteria_name = {"name": test_daac_manager_user.name}
    response = test_client.get("v2/cueusers/find", headers=headers, params=criteria_name)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_daac_manager_user.id)

def test_find_user_endpoint_no_criteria(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get("v2/cueusers/find", headers=headers, params={})
    assert response.status_code == 400

def test_get_users_by_role_endpoint(test_client, test_admin_user, test_security_user, test_daac_manager_user, test_daac_staff_user, test_daac_observer_user, test_provider_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    # admin 
    role_id = "c924d0d3-55af-49f3-bec1-d7fd4ed475e2"
    response = test_client.get(f"v2/cueusers/by_role/{role_id}", headers=headers)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_admin_user.id)

    # security
    role_id = "39677929-ba9b-426d-8c18-f607d669fcce"
    response = test_client.get(f"v2/cueusers/by_role/{role_id}", headers=headers)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_security_user.id)

    # daac_manager
    role_id = "ef872fe7-92b9-45ec-ac19-80f4c478fd36"
    response = test_client.get(f"v2/cueusers/by_role/{role_id}", headers=headers)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_daac_manager_user.id)

    # daac_staff
    role_id = "a8b3757b-dcf9-4943-8f64-5adaf17a17fe"
    response = test_client.get(f"v2/cueusers/by_role/{role_id}", headers=headers)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_daac_staff_user.id)

    # daac_observer
    role_id = "2068cc53-1232-4bc7-9647-3e29e6418e21"
    response = test_client.get(f"v2/cueusers/by_role/{role_id}", headers=headers)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_daac_observer_user.id)

    # provider 
    role_id = "0e686dba-e5b2-4302-aea0-e9ed0caff7d3"
    response = test_client.get(f"v2/cueusers/by_role/{role_id}", headers=headers)
    response_json = response.json()
    assert response_json[0].get('id') == str(test_provider_user.id)

def test_get_user_by_id_endpoint(test_client, test_admin_user, test_daac_staff_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get(f"v2/cueusers/{test_daac_staff_user.id}", headers=headers)
    response_json = response.json()
    assert response_json.get('id') == str(test_daac_staff_user.id)
    assert response_json.get('cueusername') == test_daac_staff_user.cueusername
    assert response_json.get('name') == test_daac_staff_user.name

def test_get_user_by_id_endpoint_not_found(test_client, test_admin_user, test_daac_staff_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get(f"v2/cueusers/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404

def test_get_user_by_username_endpoint(test_client, test_admin_user, test_daac_observer_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get(f"v2/cueusers/by_username/{test_daac_observer_user.cueusername}", headers=headers)
    response_json = response.json()
    assert response_json.get('id') == str(test_daac_observer_user.id)
    assert response_json.get('cueusername') == test_daac_observer_user.cueusername
    assert response_json.get('name') == test_daac_observer_user.name

def test_get_user_by_username_endpoint_does_not_exists(test_client, test_admin_user, test_daac_observer_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get(f"v2/cueusers/by_username/user_dne_user", headers=headers)
    assert response.status_code == 404

def test_update_user_endpoint(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    update_request = {"name":"new test daac manager", "email": "new_daac_manager@test.com", "edpub_id":str(uuid.uuid4()) }
    response = test_client.patch(f"v2/cueusers/{test_daac_manager_user.id}", headers=headers, json=update_request)
    response_json = response.json()
    assert response_json.get('id') == str(test_daac_manager_user.id)
    assert response_json.get('name') == update_request.get('name') 
    assert response_json.get('email') == update_request.get('email') 
    assert response_json.get('edpub_id') == str(update_request.get('edpub_id'))

def test_update_user_endpoint_not_found(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    update_request = {"name":"new test daac manager", "email": "new_daac_manager@test.com", "edpub_id":str(uuid.uuid4()) }
    response = test_client.patch(f"v2/cueusers/{uuid.uuid4()}", headers=headers, json=update_request)
    assert response.status_code == 404

def test_update_user_endpoint_no_update(test_client, test_admin_user, test_daac_manager_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.patch(f"v2/cueusers/{test_daac_manager_user.id}", headers=headers, json={})
    assert response.status_code == 400

def test_update_user_role_endpoint(test_client, test_admin_user, test_daac_observer_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    # obs to daac_staff by admin
    update_request = {"role_id": "a8b3757b-dcf9-4943-8f64-5adaf17a17fe"}
    response = test_client.patch(f"v2/cueusers/{test_daac_observer_user.id}/role", headers=headers, json=update_request)
    response_json = response.json()
    assert response_json.get('id') == str(test_daac_observer_user.id)
    assert response_json.get('roles')[0] == "daac_staff"

def test_update_user_role_endpoint_user_not_found(test_client, test_admin_user, test_daac_observer_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    update_request = {"role_id": "a8b3757b-dcf9-4943-8f64-5adaf17a17fe"}
    response = test_client.patch(f"v2/cueusers/{uuid.uuid4()}/role", headers=headers, json=update_request)
    assert response.status_code == 400 

def test_update_user_role_endpoint_role_not_found(test_client, test_admin_user, test_daac_observer_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    update_request = {"role_id": str(uuid.uuid4())}
    response = test_client.patch(f"v2/cueusers/{test_daac_observer_user.id}/role", headers=headers, json=update_request)
    assert response.status_code == 400 

def test_delete_user_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    # Create new user
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    user_id = uuid.uuid4()
    create_user_request = {"user_id": str(user_id),
                           "email": "new_user@test.com",
                           "name": "new user",
                           "cueusername":"new_user",
                           "role_id":"2068cc53-1232-4bc7-9647-3e29e6418e21",
                           "ngroup_ids":[str(test_ngroup_id)],
                           "edpub_id":None}
    response = test_client.post("v2/cueusers/", headers=headers, json=create_user_request)
    response_json = response.json()
    assert str(user_id) == response_json.get('id')

    response = test_client.get(f"v2/cueusers/{user_id}", headers=headers)
    assert response.status_code == 200

    response = test_client.delete(f"v2/cueusers/{user_id}", headers=headers)

    response = test_client.get(f"v2/cueusers/{user_id}", headers=headers)
    assert response.status_code == 404

def test_delete_user_endpoint_user_not_found(test_client, test_admin_user, test_ngroup_id, make_jwt):
    # Create new user
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.delete(f"v2/cueusers/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404