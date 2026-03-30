import uuid 


def test_submit_user_application_endpoint(test_client, test_ngroup_id, test_provider, make_jwt, mock_boto3_client):
    """Test submit user application endpoint - success."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    user_application_create_request = {
       "email": "appication@test.com",
       "name":"Test User App",
       "username": "test_user",
       "justification": "testing",
       "ngroup_id": str(test_ngroup_id),
       "account_type": "provider",
       "provider_id" : str(test_provider["id"]),
       "edpub_id": "mock_edpub_id"
    }
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    response_json = response.json()

    assert response.status_code == 201
    assert response_json["status"] == "pending"

def test_submit_user_application_endpoint_duplicate_application(test_client, test_ngroup_id, test_provider, make_jwt, mock_boto3_client):
    """Test submit user application - duplicate application."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    user_application_create_request = {
       "email": "appication@test.com",
       "name":"Test User App",
       "username": "test_user",
       "justification": "testing",
       "ngroup_id": str(test_ngroup_id),
       "account_type": "provider",
       "provider_id" : str(test_provider["id"]),
       "edpub_id": "mock_edpub_id"
    }
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    assert response.status_code == 201
    
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    assert response.status_code == 500


def test_list_all_user_applications_endpoint(test_client, test_admin_user, test_ngroup_id,
                               test_provider, make_jwt, mock_boto3_client):
    """Test list all user application endpoint - success."""
    user_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
    for i, user_id in enumerate(user_ids):
        new_user_app_jwt = make_jwt(sub=user_id)
        headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
        user_application_create_request = {
            "email": f"application{i}@test.com",
            "name": f"Test User App {i}",
            "username": "test_user",
            "justification": "testing",
            "ngroup_id": str(test_ngroup_id),
            "account_type": "provider",
            "provider_id" : str(test_provider["id"]),
            "edpub_id": "mock_edpub_id"
        }
        test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)

    test_admin_app_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_app_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}

    response = test_client.get("/v2/user_application/", headers=headers, params={"status":"pending"} )
    response_json = response.json()
    list_users = [user_app["user_id"]for user_app in response_json]
    for user_id in user_ids:
        assert user_id in list_users 

def test_get_user_application_endpoint(test_client, test_admin_user, test_ngroup_id,
                                test_provider, make_jwt, mock_boto3_client):
    """Test get user application endpoint - success."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    user_application_create_request = {
       "email": "appication@test.com",
       "name":"Test User App",
       "username": "test_user",
       "justification": "testing",
       "ngroup_id": str(test_ngroup_id),
       "account_type": "provider",
       "provider_id" : str(test_provider["id"]),
       "edpub_id": "mock_edpub_id"
    }
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    response_json_create = response.json()
    application_id = response_json_create["id"]

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get(f"/v2/user_application/{application_id}", headers=headers)
    response_json_get = response.json()
    assert response_json_create == response_json_get

def test_get_user_application_endpoint_user_not_found(test_client, test_admin_user, make_jwt, mock_boto3_client):
    """Test get user application endpoint - user not found."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    application_id = uuid.uuid4() 

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get(f"/v2/user_application/{application_id}", headers=headers)
    assert response.status_code == 404

def test_approve_user_application_endpoint(test_client, test_admin_user, test_ngroup_id,
                             test_provider, make_jwt, mock_boto3_client):
    """Test approve user application endpoint - success."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    user_application_create_request = {
       "email": "appication@test.com",
       "name":"Test User App",
       "username": "test_user",
       "justification": "testing",
       "ngroup_id": str(test_ngroup_id),
       "account_type": "provider",
       "provider_id" : str(test_provider["id"]),
       "edpub_id": "mock_edpub_id"
    }
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    response_json_create = response.json()
    application_id = response_json_create["id"]

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.post(f"/v2/user_application/{application_id}/approve",
                               headers=headers, params={"role_id":"0e686dba-e5b2-4302-aea0-e9ed0caff7d3"})
                               # give new user provider role
    response_json_approved = response.json()
    assert response_json_approved["roles"][0] == "provider"
    assert response_json_create["user_id"] == response_json_approved["id"]

def test_approve_user_application_endpoint_application_not_found(test_client, test_admin_user, make_jwt, mock_boto3_client):
    """Test approve user application endpoint - application does not exist."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    application_id = uuid.uuid4()

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.post(f"/v2/user_application/{application_id}/approve",
                               headers=headers, params={"role_id":"0e686dba-e5b2-4302-aea0-e9ed0caff7d3"})
                               # give new user provider role
    assert response.status_code == 404

def test_approve_user_application_endpoint_no_permission(test_client, test_daac_observer_user, test_ngroup_id,
                                           test_provider, make_jwt, mock_boto3_client):
    """Test approve user application endpoint - user does not have privilege."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    user_application_create_request = {
       "email": "appication@test.com",
       "name":"Test User App",
       "username": "test_user",
       "justification": "testing",
       "ngroup_id": str(test_ngroup_id),
       "account_type": "provider",
       "provider_id" : str(test_provider["id"]),
       "edpub_id": "mock_edpub_id"
    }
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    response_json_create = response.json()
    application_id = response_json_create["id"]

    test_daac_obs_user_jwt = make_jwt(sub=str(test_daac_observer_user.id))
    headers = {"Authorization": f"Bearer {test_daac_obs_user_jwt}"}
    response = test_client.post(f"/v2/user_application/{application_id}/approve",
                               headers=headers, params={"role_id":"0e686dba-e5b2-4302-aea0-e9ed0caff7d3"})
                               # give new user provider role
    assert response.status_code == 403

def test_reject_user_application_endpoint(test_client, test_admin_user, test_ngroup_id,
                                     test_provider, make_jwt, mock_boto3_client):
    """Test reject user application endpoint - success."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    user_application_create_request = {
       "email": "appication@test.com",
       "name":"Test User App",
       "username": "test_user",
       "justification": "testing",
       "ngroup_id": str(test_ngroup_id),
       "account_type": "provider",
       "provider_id" : str(test_provider["id"]),
       "edpub_id": "mock_edpub_id"
    }
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    response_json_create = response.json()
    application_id = response_json_create["id"]

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.post(f"/v2/user_application/{application_id}/reject", headers=headers)
    response_json_rejected = response.json()

    assert response_json_create["id"] == response_json_rejected["id"]
    assert response_json_rejected["status"] == "rejected"

def test_reject_user_application_endpoint_application_not_found(test_client, test_admin_user, make_jwt, mock_boto3_client):
    """Test reject user application endpoint - application does not exist."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    application_id = uuid.uuid4()

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.post(f"/v2/user_application/{application_id}/reject", headers=headers)
    response_json_rejected = response.json()

    assert response.status_code == 404

def test_reject_user_application_endpoint_no_permission(test_client, test_daac_observer_user, test_ngroup_id,
                                                   test_provider, make_jwt, mock_boto3_client):
    """Test reject user application endpoint - user does not have privilege."""
    new_user_app_jwt = make_jwt(sub=str(uuid.uuid4()))
    headers = {"Authorization": f"Bearer {new_user_app_jwt}"}
    user_application_create_request = {
       "email": "appication@test.com",
       "name":"Test User App",
       "username": "test_user",
       "justification": "testing",
       "ngroup_id": str(test_ngroup_id),
       "account_type": "provider",
       "provider_id" : str(test_provider["id"]),
       "edpub_id": "mock_edpub_id"
    }
    response = test_client.post("/v2/user_application/", headers=headers, json=user_application_create_request)
    response_json_create = response.json()
    application_id = response_json_create["id"]

    test_daac_obs_user_jwt = make_jwt(sub=str(test_daac_observer_user.id))
    headers = {"Authorization": f"Bearer {test_daac_obs_user_jwt}"}
    response = test_client.post(f"/v2/user_application/{application_id}/reject", headers=headers)

    assert response.status_code == 403