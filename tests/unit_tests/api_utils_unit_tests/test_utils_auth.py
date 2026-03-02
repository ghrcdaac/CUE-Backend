import pytest
from typing import Tuple
import uuid

from app.v2.utils.auth import get_keycloak_client, get_user_login_status, KeycloakClient
from app.v2.utils.user_application import submit_application

@pytest.mark.asyncio
async def test_get_keycloak_client(make_request):
    req = make_request()
    keycloak_client = get_keycloak_client(req)
    assert isinstance(keycloak_client, KeycloakClient)

@pytest.mark.asyncio
async def test_keycloak_client(make_request):
    req = make_request()
    keycloak_client = get_keycloak_client(req)
    result = keycloak_client.get_login_url()
    assert isinstance(result,Tuple)
    assert isinstance(result[0],str)
    assert isinstance(result[1],str)
    
@pytest.mark.asyncio
async def test_exchange_code_for_tokens(make_request):
    mock_code = "mock_code"
    mock_redirect_uri = "https://localhost:3000/callback_test"

    req = make_request()
    keycloak_client = get_keycloak_client(req)
    response_json = await keycloak_client.exchange_code_for_tokens(mock_code, mock_redirect_uri)
    assert response_json["access_token"] == "ey.mock.exchanged.jwt"
    assert response_json["expires_in"] == 300
    assert response_json["refresh_expires_in"] == 1800
    assert response_json["refresh_token"] == "ey.mock.refresh.jwt"
    assert response_json["token_type"] == "Bearer"

@pytest.mark.asyncio
async def test_create_user(make_request):
    email = "test_user@test.com"
    username = "test_user"
    first_name = "test"
    last_name = "user"

    req = make_request()
    keycloak_client = get_keycloak_client(req)

    response_json = await keycloak_client.create_user(email, username, first_name, last_name)
    assert uuid.UUID(response_json)

@pytest.mark.asyncio
async def test_refresh_access_token(make_request):
    req = make_request()
    keycloak_client = get_keycloak_client(req)
    mock_token = "mock_token"
    response_json = await keycloak_client.refresh_access_token(mock_token)
    assert response_json['access_token'] == 'ey.mock.new.access.jwt'
    assert response_json['expires_in'] == 300
    assert response_json['refresh_expires_in'] == 1800
    assert response_json['refresh_token'] == 'ey.mock.new.refresh.jwt'
    assert response_json['token_type']== 'Bearer'
    assert response_json['not-before-policy']== 0
    assert response_json['session_state'] == 'b6f2c0d5-2c6d-4c7f-9a9d-1234567890ab'
    assert response_json['scope'] == 'openid profile email'
    assert response_json['id_token'] == 'ey.mock.id.jwt'

@pytest.mark.asyncio
async def test_delete_user(make_request):
    req = make_request()
    keycloak_client = get_keycloak_client(req)
    user_id = uuid.uuid4()
    await keycloak_client.delete_user(user_id)

@pytest.mark.asyncio
async def test_initiate_password_reset(make_request):
    req = make_request()
    keycloak_client = get_keycloak_client(req)
    user_id = uuid.uuid4()
    await keycloak_client.initiate_password_reset(user_id)

@pytest.mark.asyncio
async def test_introspect_token(make_request):
    req = make_request()
    keycloak_client = get_keycloak_client(req)
    mock_token = "mock_token"
    response_json = await keycloak_client.introspect_token(mock_token)
    assert response_json["mock_key"] == "mock_data"

@pytest.mark.asyncio
async def test_get_user_login_status(make_request, test_admin_user, make_user_application_create):
    req = make_request()
    registered_response = await get_user_login_status(req, test_admin_user.id)
    assert registered_response == "registered" 

    unregistered_response = await get_user_login_status(req, uuid.uuid4())
    assert unregistered_response == "unregistered" 

    mock_user_application = make_user_application_create("test_user@test.com", "test_user", "test_username", "test", "daac")
    user_id = uuid.uuid4()
    await submit_application(req, mock_user_application, user_id)

    unregistered_response = await get_user_login_status(req, user_id)
    assert unregistered_response == "pending_approval" 