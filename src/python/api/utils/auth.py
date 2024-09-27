import os
import jwt
import requests
import base64

from lambda_utils.type_util.auth import auth_token

providerUrl = os.environ.get('AUTH_PROVIDER_URL')
loginPath = os.environ.get('AUTH_LOGIN_PATH')
logoutPath = os.environ.get('AUTH_LOGOUT_PATH')
tokenPath = os.environ.get('AUTH_TOKEN_PATH')

clientRoot = os.environ.get('CLIENT_ROOT_URL')
clientId = os.environ.get('AUTH_CLIENT_ID')
clientSecret = os.environ.get('AUTH_CLIENT_SECRET')
clientPath = os.environ.get('AUTH_CLIENT_PATH')

async def _buildRedirectUrl(baseUrl: str, queryParams: dict) -> str:
    for key, value in queryParams.items():
        if type(value) == list:
            baseUrl += f'{key}={"+".join(value)}&'
        else:
            baseUrl += f'{key}={value}&'
    return baseUrl[:-1]

async def _tokenService(**kwargs) -> dict:
    data = kwargs
    endpoint = f'{providerUrl}/{tokenPath}'
    creds = base64.b64encode(f'{clientId}:{clientSecret}'.encode('utf-8'))
    headers = {
        'Authorization': f'Basic {creds.decode("utf-8")}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(endpoint, data=data, headers=headers)
    return response.json()

async def getToken(code) -> auth_token:
    clientUri = f'{clientRoot}/{clientPath}'
    tokens = await _tokenService(
        code=code,
        grantType='authorization_code',
        redirectUri=clientUri
    )
    resp = auth_token(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        id_token=tokens['id_token'] if 'id_token' in tokens else None
    )
    return resp

async def refreshToken(token):
    tokens = await _tokenService(
        grantType='refresh_token',
        refresh_token=token
    )
    resp = auth_token(
        access_token=jwt.decode(tokens['access_token']),
        refresh_token=jwt.decode(tokens['refresh_token']),
        id_token=jwt.decode(tokens['id_token'])
    )
    return resp

async def getLoginUrl(state: str) -> str:
    clientUri = f'{clientRoot}/{clientPath}'
    redirectUrl = f'{providerUrl}/{loginPath}'
    searchParams = {
        'client_id': clientId,
        'redirect_uri': clientUri,
        'scope': ['openid', 'aws.cognito.signin.user.admin'],
        'response_type': 'code',
        'state': state
    }
    return(await _buildRedirectUrl(redirectUrl, searchParams))

async def getLogoutUrl(host: str) -> str:
    clientUri = f'{host}/{clientPath}'
    redirectUrl = f'{providerUrl}/{logoutPath}'
    searchParams = {
        'client_id': clientId,
        'logout_uri': clientUri
    }
    return(await _buildRedirectUrl(redirectUrl, searchParams))