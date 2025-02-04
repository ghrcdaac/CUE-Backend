import os
import boto3
import hmac, hashlib, base64
from pydantic import SecretStr
from lambda_utils.type_util.auth import login

_PoolId = os.environ.get('POOL_ID')
_ClientId = os.environ.get('CLIENT_ID')
_ClientSecret = os.environ.get('CLIENT_SECRET')

def _decript_secret(secret: SecretStr) -> SecretStr:
    return secret

def _get_secret_hash(secret_name:str='') -> SecretStr:
    key = bytes(_ClientSecret, 'utf-8')
    message = bytes(secret_name+_ClientId, 'utf-8')
    secret_hash = base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()
    return secret_hash

def logIn(param: login):
    username = param.username
    password = _decript_secret(param.password)
    secret_hash = _get_secret_hash(username)
    client = boto3.client('cognito-idp')
    response = client.admin_initiate_auth(
        UserPoolId=_PoolId,
        ClientId=_ClientId,
        AuthFlow='ADMIN_USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password.get_secret_value(),
            'SECRET_HASH': secret_hash
        }
    )
    print(response)
    return response

def logOut(username: str):
    client = boto3.client('cognito-idp')
    _=client.admin_user_global_sign_out(
        UserPoolId='test',
        Username=username
    )
    return 'logout'

def refreshToken(token: str):
    client = boto3.client('cognito-idp')
    
    return 'refresh'
    