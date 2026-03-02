import pytest
import os

def test_get_login_url(test_client):
    response = test_client.get("v2/auth/login-url")
    response_json = response.json()
    assert response_json.get("login_url")
    assert response_json.get("state")

def test_exchange_code(test_client):
    body = {"code": "mock_code", "redirect_uri":os.getenv("FRONTEND_CALLBACK_URL"), "state":"mock_state"}
    response = test_client.post("v2/auth/exchange-code", json=body)
    response_json = response.json()  
    assert response_json.get("access_token")
    assert response_json.get("expires_in")
    assert response_json.get("id_token")
    assert response_json.get("token_type")

def test_get_user_status(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    bearer_token = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get("v2/auth/status", headers=bearer_token)
    response_json = response.json()
    assert response_json.get('status') == 'registered'

def test_get_user_claims_for_registration(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), email=test_admin_user.email, cueusername=test_admin_user.cueusername, name=test_admin_user.name)
    bearer_token = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get("v2/auth/claims", headers=bearer_token)
    response_json = response.json()
    assert response_json.get('name') == test_admin_user.name
    assert response_json.get('email') == test_admin_user.email
    assert response_json.get('cueusername') == test_admin_user.cueusername

def test_refresh_token(test_client):
    response = test_client.post("v2/auth/refresh", json={"refresh_token": "mock_refresh_token"})
    response_json = response.json()
    assert response_json.get('access_token')
    assert response_json.get('token_type')
    assert response_json.get('expires_in')
    assert response_json.get('refresh_token')

def test_get_user_info(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), email=test_admin_user.email, cueusername=test_admin_user.cueusername, name=test_admin_user.name)
    bearer_token = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.get("v2/auth/userinfo", headers=bearer_token)
    response_json = response.json()
    assert response_json.get('sub') == str(test_admin_user.id)
    assert response_json.get('ngroups') == test_admin_user.ngroups
    assert response_json.get('privileges') 

def test_logout(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), email=test_admin_user.email, cueusername=test_admin_user.cueusername, name=test_admin_user.name)
    response = test_client.post("v2/auth/logout-url", json={"id_token_hint":test_admin_user_jwt})
    response_json = response.json() 
    assert response_json.get('logout_url')

def test_initiate_password_reset(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), email=test_admin_user.email, cueusername=test_admin_user.cueusername, name=test_admin_user.name)
    bearer_token = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    response = test_client.post("v2/auth/initiate-password-reset", headers=bearer_token)
    response_json = response.json() 
    assert response_json.get('message') == "Password reset process initiated. Please check your email."

def test_introspect_token(test_client, test_admin_user, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id), email=test_admin_user.email, cueusername=test_admin_user.cueusername, name=test_admin_user.name)
    response = test_client.post("v2/auth/introspect", json={"token":test_admin_user_jwt, "token_type_hint": "access_token"})
    response_json = response.json()
    assert response_json