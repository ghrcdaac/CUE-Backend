import os
import requests
import logging
import jwt
from fastapi import Depends, HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from utils.JWTBearer import JWTBearer  # Import JWTBearer
# from lambda_utils.type_util.auth import JWKS  # Import JWKS

logger = logging.getLogger(__name__)

_PoolId = os.environ.get('POOL_ID')
_ClientId = os.environ.get('CLIENT_ID')
_Region = os.environ.get('AWS_REGION')

# --- JWKS Fetching (at startup) ---
jwks = None

async def fetch_jwks():
    """Fetches the JWKS from Cognito."""
    global jwks
    try:
        jwks_url = f'https://cognito-idp.{_Region}.amazonaws.com/{_PoolId}/.well-known/jwks.json'
        response = requests.get(jwks_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        jwks = JWKS(**response.json())  # Use Pydantic model
        return jwks
    except requests.exceptions.RequestException as e:
        logger.critical(f"Failed to fetch JWKS: {e}")
        # Consider retrying or using a cached version in a real application
        raise

auth_scheme = None

async def startup_auth():
    """Initializes the JWTBearer instance."""
    global auth_scheme
    jwks_data = await fetch_jwks()  # Await the fetch
    auth_scheme = JWTBearer(jwks_data)  # Pass the data, not the URL


# --- REMOVE get_current_user ---
# We don't need this function in the simplified version.