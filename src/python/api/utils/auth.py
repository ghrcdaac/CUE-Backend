import os
import boto3
import hmac, hashlib, base64
import requests
from asyncpg.pool import Pool
from pydantic import SecretStr
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.type_util.auth import login, auth_response, pwd_response, JWKS
from lambda_utils.database_util import cueuser as cueuser_db
from fastapi import Depends, HTTPException
from starlette.status import HTTP_403_FORBIDDEN
import logging

from utils.JWTBearer import JWTBearer, JWTAuthorizationCredentials
from utils.cueuser import get_cueuser_by_lookup
from utils.role_privilege import list_privileges_for_role
from lambda_utils.type_util.cueuser import CueuserAuth

logger = logging.getLogger(__name__)

_PoolId = os.environ.get('POOL_ID')
_ClientId = os.environ.get('CLIENT_ID')
_ClientSecret = os.environ.get('CLIENT_SECRET')
_Region = os.environ.get('AWS_REGION')

jwks = JWKS.parse_obj(requests.get(f'https://cognito-idp.{_Region}.amazonaws.com/{_PoolId}/.well-known/jwks.json').json())

auth = JWTBearer(jwks)



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
    client = boto3.client('cognito-idp', region_name=_Region)
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
    client = boto3.client('cognito-idp', region_name=_Region)
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
    client = boto3.client('cognito-idp', region_name=_Region)
    _=client.admin_user_global_sign_out(
        UserPoolId=_PoolId,
        Username=username
    )
    return True

def refreshToken(token: str):
    client = boto3.client('cognito-idp')
    
    return 'refresh'

async def get_current_user(credentials: JWTAuthorizationCredentials = Depends(auth)) -> CueuserAuth:
    pool: Pool = await get_connection_pool()
    try:
        uname = credentials.claims['username']
        params = (str(uname),)
        user:CueuserAuth = (await query(pool, cueuser_db.get_cueuser_by_username, params, row_mapper=CueuserAuth.from_db_row))[0]
        user.privilages = await list_privileges_for_role(user.role_id)
        return CueuserAuth.model_validate(user)
    except KeyError:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="JWK invalid")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid token")