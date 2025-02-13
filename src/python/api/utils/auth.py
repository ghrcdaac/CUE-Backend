import os
import boto3
import requests
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.type_util.auth import JWKS, AuthResponse, RefreshTokenRequest
from fastapi import Depends, HTTPException
from starlette.status import HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST
import logging

from utils.JWTBearer import JWTBearer, JWTAuthorizationCredentials
from lambda_utils.database_util import cueuser as cueuser_db
from utils.cueuser import get_cueuser_by_username
from utils.role_privilege import list_privileges_for_role
from lambda_utils.type_util.cueuser import CueuserAuth, CueuserReturn

logger = logging.getLogger(__name__)

_PoolId = os.environ.get('POOL_ID')
_ClientId = os.environ.get('CLIENT_ID')
_Region = os.environ.get('AWS_REGION')

# Fetch JWKS at startup
jwks = None

async def fetch_jwks():
    """Fetches the JWKS from Cognito."""
    global jwks
    try:
        jwks_url = f'https://cognito-idp.{_Region}.amazonaws.com/{_PoolId}/.well-known/jwks.json'
        response = requests.get(jwks_url)
        response.raise_for_status()
        jwks = JWKS(**response.json())
        return jwks  # Return the fetched JWKS
    except requests.exceptions.RequestException as e:
        logger.critical(f"Failed to fetch JWKS: {e}")
        # Consider retrying or using a cached version in a real application
        raise

auth_scheme = None  # Initialize to None

async def startup_auth():
    """Initializes the JWTBearer instance with the fetched JWKS."""
    global auth_scheme
    jwks_data = await fetch_jwks()
    auth_scheme = JWTBearer(jwks_data)

# --- Authentication Logic (get_current_user remains the same) ---

async def get_current_user(credentials: JWTAuthorizationCredentials = Depends(auth_scheme)) -> CueuserAuth: # Using our class
    pool: Pool = await get_connection_pool()
    try:
        uname = credentials.claims['username']
        params = (str(uname),)
        # Fetch user information. Use get_cueuser_by_username, and adapt
        # from_db_row in CueuserReturn to handle the result.
        result = await query(pool, cueuser_db.get_cueuser_by_username, params, row_mapper=CueuserAuth.from_db_row)

        if not result:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="User not found")
        user = result[0]

        # The following line assumes that list_privileges_for_role exists.
        if user.role_name:
            user.privilages = await list_privileges_for_role(user.role_name)  # type: ignore # Passing the role name
        else:
            user.privilages = []
        return user

    except KeyError:
        await pool.close()
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="JWK invalid")
    except Exception as e:
        logger.error(f"Error getting current user: {e}", exc_info=True)
        await pool.close()
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=f"Invalid token: {e}")
    finally:
        await pool.close()


async def verify_and_get_user(token: str) -> CueuserReturn:
    """
    Verifies a JWT and retrieves the associated user from the database.
    This function *combines* JWT validation and user retrieval.
    """
    try:
        # Validate the token using JWTBearer.  This will raise an exception if invalid.
        payload = auth_scheme.verify_jwk_token(token)
        # Create a mock credentials object.  This is a bit of a workaround
        # to reuse our existing get_current_user function.
        credentials = JWTAuthorizationCredentials(claims=payload)
        return await get_current_user(credentials)

    except HTTPException as e:
        # Re-raise HTTP exceptions directly.
        raise
    except Exception as e:
        logger.error(f"Error verifying token and getting user: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Token verification failed: {e}")



async def refresh_token(request: RefreshTokenRequest) -> AuthResponse:
    """Refreshes an access token using a refresh token."""
    client = boto3.client('cognito-idp', region_name=_Region)
    try:
        response = client.initiate_auth(
            ClientId=_ClientId,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': request.refresh_token,
                # 'SECRET_HASH': _get_secret_hash(username)  # Only needed if using a client secret!
            }
        )

        if 'AuthenticationResult' in response:
             return AuthResponse(
                access_token=response['AuthenticationResult']['AccessToken'],
                #refresh_token = response['AuthenticationResult']['RefreshToken'], #Cognito *sometimes* returns
                id_token = response['AuthenticationResult']['IdToken'] #best practice to return
            )
        else:
            # Handle cases where refresh token is invalid/expired
            raise HTTPException(status_code=401, detail="Invalid refresh token")

    except client.exceptions.NotAuthorizedException as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from e
    except Exception as e:
        logger.error(f"Error during token refresh: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


async def forgot_password(username: str):
    """Initiates the forgot password flow."""
    client = boto3.client('cognito-idp', region_name=_Region)
    try:
        response = client.forgot_password(
            ClientId=_ClientId,
            Username=username,
            # SecretHash=_get_secret_hash(username)  # Only include if using a client secret!
        )
        return response  # Return Cognito's response (info about where code was sent)
    except client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error initiating forgot password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error initiating forgot password")