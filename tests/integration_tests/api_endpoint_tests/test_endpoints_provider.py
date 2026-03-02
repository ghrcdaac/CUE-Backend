import pytest
import uuid

def test_create_provider_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider",
                               "long_name": "New Provider",
                               "can_upload":True}
    response = test_client.post("/v2/providers/", headers=headers, json=create_provider_request)
    response_json = response.json()

    assert response_json.get("id")
    assert response_json.get("short_name") == create_provider_request["short_name"]
    assert response_json.get("long_name") == create_provider_request["long_name"]
    assert response_json.get("ngroup_id") == create_provider_request["ngroup_id"]
    assert response_json.get("point_of_contact") == create_provider_request["point_of_contact"]

def test_create_provider_endpoint_bad_poc(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(uuid.uuid4()),
                               "short_name": "new_provider",
                               "long_name": "New Provider",
                               "can_upload":True}
    response = test_client.post("/v2/providers/", headers=headers, json=create_provider_request)
    assert response.status_code == 400


def test_list_providers_for_application_form(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request1 = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider1",
                               "long_name": "New Provider1",
                               "can_upload":True}
    provider_response1 = test_client.post("/v2/providers/", headers=headers, json=create_provider_request1).json()
    create_provider_request2 = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider2",
                               "long_name": "New Provider2",
                               "can_upload":True}
    provider_response2 = test_client.post("/v2/providers/", headers=headers, json=create_provider_request2).json()
    create_provider_request3 = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider3",
                               "long_name": "New Provider3",
                               "can_upload":True}
    provider_response3 = test_client.post("/v2/providers/", headers=headers, json=create_provider_request3).json()
    provider_ids = sorted([provider_response1["id"], provider_response2["id"], provider_response3["id"]]) 
    list_response_json = test_client.get("/v2/providers/for-application-form", params={"ngroup_id":str(test_ngroup_id)}, headers=headers).json()

    assert provider_ids[0] in [provider["id"] for provider in list_response_json]
    assert provider_ids[1] in [provider["id"] for provider in list_response_json]
    assert provider_ids[2] in [provider["id"] for provider in list_response_json]

def test_list_providers_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id":str(test_ngroup_id)}
    create_provider_request1 = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider1",
                               "long_name": "New Provider1",
                               "can_upload":True}
    provider_response1 = test_client.post("/v2/providers/", headers=headers, json=create_provider_request1).json()
    create_provider_request2 = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider2",
                               "long_name": "New Provider2",
                               "can_upload":True}
    provider_response2 = test_client.post("/v2/providers/", headers=headers, json=create_provider_request2).json()
    create_provider_request3 = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider3",
                               "long_name": "New Provider3",
                               "can_upload":True}
    provider_response3 = test_client.post("/v2/providers/", headers=headers, json=create_provider_request3).json()
    provider_ids = sorted([provider_response1["id"], provider_response2["id"], provider_response3["id"]]) 
    list_response_json = test_client.get("/v2/providers/", headers=headers).json()

    assert provider_ids[0] in [provider["id"] for provider in list_response_json]
    assert provider_ids[1] in [provider["id"] for provider in list_response_json]
    assert provider_ids[2] in [provider["id"] for provider in list_response_json]

def test_get_provider_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider",
                               "long_name": "New Provider",
                               "can_upload":True}
    response = test_client.post("/v2/providers/", headers=headers, json=create_provider_request)
    response_json = response.json()
    provider_id = response_json.get("id")

    response = test_client.get(f"/v2/providers/{provider_id}", headers=headers)
    response_json = response.json()

    assert response_json.get("id") == provider_id
    assert response_json.get("short_name") == create_provider_request["short_name"]
    assert response_json.get("long_name") == create_provider_request["long_name"]
    assert response_json.get("ngroup_id") == create_provider_request["ngroup_id"]
    assert response_json.get("point_of_contact") == create_provider_request["point_of_contact"]

def test_get_provider_endpoint_not_found(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    provider_id = uuid.uuid4()

    response = test_client.get(f"/v2/providers/{provider_id}", headers=headers)

    assert response.status_code == 404

def test_update_provider_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider",
                               "long_name": "New Provider",
                               "can_upload":True}
    response = test_client.post("/v2/providers/", headers=headers, json=create_provider_request)
    response_json = response.json()
    provider_id = response_json.get("id")

    update_provider_request = {"short_name": "not_new_provider",
                               "long_name": "Not New Provider",
                               "can_upload": False,
                               "reason": "testing"}
    response = test_client.patch(f"/v2/providers/{provider_id}", headers=headers, json=update_provider_request)
    response_json = response.json()

    assert response_json.get("id") == provider_id
    assert response_json.get("short_name") == update_provider_request["short_name"]
    assert response_json.get("long_name") == update_provider_request["long_name"]
    assert not response_json.get("can_upload")
    assert response_json.get("reason") == update_provider_request["reason"]

def test_update_provider_endpoint_not_found(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    provider_id = uuid.uuid4()

    update_provider_request = {"short_name": "not_new_provider",
                               "long_name": "Not New Provider",
                               "can_upload": False,
                               "reason": "testing"}
    response = test_client.patch(f"/v2/providers/{provider_id}", headers=headers, json=update_provider_request)

    assert response.status_code == 404

def test_update_provider_endpoint_empty_update(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider",
                               "long_name": "New Provider",
                               "can_upload":True}
    response = test_client.post("/v2/providers/", headers=headers, json=create_provider_request)
    response_json = response.json()
    provider_id = response_json.get("id")

    update_provider_request = {}
    response = test_client.patch(f"/v2/providers/{provider_id}", headers=headers, json=update_provider_request)

    assert response.status_code == 400 

def test_update_provider_endpoint_no_access(test_client, test_admin_user, test_daac_observer_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    admin_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider",
                               "long_name": "New Provider",
                               "can_upload":True}
    response = test_client.post("/v2/providers/", headers=admin_headers, json=create_provider_request)
    response_json = response.json()
    provider_id = response_json.get("id")

    test_daac_obs_user_jwt = make_jwt(sub=str(test_daac_observer_user.id), roles=test_daac_observer_user.roles, ngroups=test_daac_observer_user.ngroups)
    daac_obs_headers = {"Authorization": f"Bearer {test_daac_obs_user_jwt}"}
    update_provider_request = {"short_name": "not_new_provider",
                               "long_name": "Not New Provider",
                               "can_upload": False,
                               "reason": "testing"}
    response = test_client.patch(f"/v2/providers/{provider_id}", headers=daac_obs_headers, json=update_provider_request)

    assert response.status_code == 403

def test_delete_provider_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    create_provider_request = {"ngroup_id": str(test_ngroup_id),
                               "point_of_contact": str(test_admin_user.id),
                               "short_name": "new_provider",
                               "long_name": "New Provider",
                               "can_upload":True}
    response = test_client.post("/v2/providers/", headers=headers, json=create_provider_request)
    response_json = response.json()
    provider_id = response_json.get("id")

    response = test_client.get(f"/v2/providers/{provider_id}", headers=headers)
    assert response.status_code == 200

    response = test_client.delete(f"/v2/providers/{provider_id}", headers=headers)
    assert response.status_code == 204

    response = test_client.get(f"/v2/providers/{provider_id}", headers=headers)
    assert response.status_code == 404

def test_delete_provider_endpoint_not_found(test_client, test_admin_user, test_ngroup_id, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), roles=test_admin_user.roles, ngroups=test_admin_user.ngroups)
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    provider_id = uuid.uuid4()

    response = test_client.get(f"/v2/providers/{provider_id}", headers=headers)
    assert response.status_code == 404
