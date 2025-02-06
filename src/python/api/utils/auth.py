import os
import boto3
import hmac, hashlib, base64
from pydantic import SecretStr
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.type_util.auth import login, auth_response, pwd_response
from lambda_utils.database_util import cueuser as cueuser_db
import logging

logger = logging.getLogger(__name__)

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

async def logIn(param: login) -> auth_response:
    username = param.username
    password = _decript_secret(param.password)
    secret_hash = _get_secret_hash(username)
    client = boto3.client('cognito-idp', region_name=os.environ.get('AWS_REGION'))
    pool: Pool = await get_connection_pool()
    try:
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
        if 'Session' in response:
            return {'session': response['Session']}
        
        # login db update
        await query(pool, cueuser_db.login_cueuser, 
                    (response['AuthenticationResult']['RefreshToken'], username))
        
        return {'access_token': response['AuthenticationResult']['AccessToken']}
    except client.exceptions.NotAuthorizedException:
        raise ValueError('Invalid username or password')
    except Exception as e:
        logger.error(e)
        raise
    

async def pwdResponse(param: pwd_response) -> auth_response:
    username = param.username
    password = _decript_secret(param.password)
    secret_hash = _get_secret_hash(username)
    client = boto3.client('cognito-idp', region_name='us-west-2')
    pool = await get_connection_pool()
    try:
        resp = client.admin_respond_to_auth_challenge(
            UserPoolId=_PoolId,
            ClientId=_ClientId,
            ChallengeName='NEW_PASSWORD_REQUIRED',
            Session=param.session,
            ChallengeResponses={
                'USERNAME': username,
                'NEW_PASSWORD': password.get_secret_value(),
                "SECRET_HASH": secret_hash,
            }
        )
        # login db update
        await query(pool, cueuser_db.login_cueuser, 
                    (resp['AuthenticationResult']['RefreshToken'], username))
        return {'access_token': resp['AuthenticationResult']['AccessToken']}
    except Exception as e:
        logger.error(e)
        raise

async def logOut(username: str) -> bool:
    client = boto3.client('cognito-idp', region_name='us-west-2')
    _=client.admin_user_global_sign_out(
        UserPoolId=_PoolId,
        Username=username
    )
    return True

def refreshToken(token: str):
    client = boto3.client('cognito-idp')
    
    return 'refresh'
    