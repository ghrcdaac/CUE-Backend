from fastapi import HTTPException, status, Request, Depends
import asyncio
import os
import time
from typing import Optional
import logging 
from uuid import UUID 
import boto3
import requests
from jose import jwk, jwt
from jose.utils import base64url_decode
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
import lambda_utils.database_util.cueuser_auth as cueuser_auth_db
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer

from utils import cueuser

logger = logging.getLogger(__name__)



class CognitoAuth:

    def __init__(self):
        logger.info("Initializing CognitoAuth instance and reading environment variables...")
        self.region = os.environ.get("AWS_REGION", "us-west-2") 
        self.user_pool_id = os.environ["POOL_ID"]
        self.client_id = os.environ["CLIENT_ID"]
        self.client = boto3.client("cognito-idp", region_name=self.region)
        self._keys = None
        self._keys_fetched_at = 0 

    def _fetch_keys(self):
        """Fetches and caches Cognito's public keys."""
        # Cache for 1 hour
        if self._keys is None or time.time() - self._keys_fetched_at > 3600:
            logger.info("Fetching Cognito JWKS keys...")
            url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            response = requests.get(url)
            response.raise_for_status()
            self._keys = response.json()
            self._keys["fetched_at"] = time.time()
        return self._keys["keys"]
    
    async def _get_user(self, claims):
        pool: Pool = await get_connection_pool()
        user_id = claims['sub']
        params = (user_id,)
        try:
            user = await query(pool, cueuser_auth_db.get_cueuser_from_auth, params, row_mapper=CueuserAuthBearer.from_db_row)
            print(user)
            return dict(user[0])
        except Exception as e:
            print(f"Error retrieving user from database: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
        finally:
            await pool.close()

    def get_current_user(self, request: Request) -> Optional[dict]:
        """Verifies the access token and retrieves user attributes."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("Authorization header missing")
            # Return None, let dependency handle raising 401 if needed by caller
            return None
        try:
            if not auth_header.startswith("Bearer "):
                 raise ValueError("Invalid Authorization header format")
            bearer_token = auth_header.split(" ")[1]
            temp = self.verify_token(bearer_token)
            return temp
        except Exception:
            return None

    def verify_token(self, token: str) -> dict:
        """Verifies a JWT token against the Cognito User Pool."""
        keys = self._fetch_keys()
        try:
            headers = jwt.get_unverified_header(token)
            kid = headers.get('kid')
            if not kid:
                 raise ValueError("'kid' not found in token headers")

        except Exception as e:
            logger.error(f"Error parsing token headers: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token headers')

        key_index = -1
        for i, key in enumerate(keys):
             if kid == key.get('kid'):
                 key_index = i
                 break
        if key_index == -1:
            logger.error(f"Public key not found for kid: {kid}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Public key not found in jwks.json')

        try:
            public_key = jwk.construct(keys[key_index])
            message, encoded_signature = str(token).rsplit('.', 1)
            decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

            if not public_key.verify(message.encode("utf8"), decoded_signature):
                logger.warning("Token signature verification failed.")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Signature verification failed')

            claims = jwt.get_unverified_claims(token) # Claims are verified by signature check now

            if time.time() > claims.get('exp', 0):
                logger.warning("Token is expired.")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token is expired')

            # Use 'aud' if present (ID token), else 'client_id' (Access token)
            audience = claims.get('aud') or claims.get('client_id')
            if audience != self.client_id:
                logger.warning(f"Token audience '{audience}' does not match client ID.")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token was not issued for this application')

            user =  asyncio.run(self._get_user(claims))
            return user
        
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"An unexpected error occurred: {str(e)}")

    def refresh_tokens(self, refresh_token: str) -> dict:
        """Refreshes access and ID tokens using a refresh token."""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={'REFRESH_TOKEN': refresh_token},
            )
            auth_result = response['AuthenticationResult']
            return {
                "access_token": auth_result['AccessToken'],
                "id_token": auth_result['IdToken'],
                "expires_in": auth_result['ExpiresIn'],
                "token_type": auth_result['TokenType']
            }
        except self.client.exceptions.NotAuthorizedException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.  Please log in again.",
            ) from e
        except self.client.exceptions.UserNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User not found."
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}",
            ) from e

    def verify_email(self, access_token: str) -> dict:
        """Verifies if the user's email is verified in Cognito."""
        try:
            response = self.client.get_user(AccessToken=access_token)
            for attr in response['UserAttributes']:
                if attr['Name'] == 'email_verified':
                    return {'email_verified': attr['Value'] == 'true'}
            return {'email_verified': False}
        except self.client.exceptions.NotAuthorizedException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    def forgot_password(self, username: str) -> dict:
        """Initiates the forgot password flow."""
        try:
            response = self.client.forgot_password(
                ClientId=self.client_id,
                Username=username
            )
            return {
                "code_delivery_details": response["CodeDeliveryDetails"]
            }
        except self.client.exceptions.UserNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from e
        except self.client.exceptions.InvalidParameterException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except self.client.exceptions.LimitExceededException as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    def confirm_forgot_password(self, username: str, confirmation_code: str, new_password: str) -> None:
        """Confirms the forgot password flow with the code and new password."""
        try:
            self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                Password=new_password
            )
        except self.client.exceptions.UserNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from e
        except self.client.exceptions.CodeMismatchException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code"
            ) from e
        except self.client.exceptions.ExpiredCodeException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired"
            ) from e
        except self.client.exceptions.InvalidPasswordException as e:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except self.client.exceptions.LimitExceededException as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    def change_password(self, access_token: str, previous_password: str, new_password: str) -> None:
        """Changes the user's password (requires the user to be logged in)."""
        try:
            self.client.change_password(
                AccessToken=access_token,
                PreviousPassword=previous_password,
                ProposedPassword=new_password
            )
        except self.client.exceptions.NotAuthorizedException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
            ) from e
        except self.client.exceptions.InvalidPasswordException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except self.client.exceptions.LimitExceededException as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    def admin_verify_email(self, username: str) -> None:
        """
        Sets the 'email_verified' attribute to 'true' for a given user.
        Requires admin privileges.
        """
        try:
            self.client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {"Name": "email_verified", "Value": "true"}
                ]
            )
        except self.client.exceptions.UserNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from e
        except self.client.exceptions.NotAuthorizedException as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,  # Use 403 for insufficient permissions
                detail="Insufficient permissions to verify email. Requires admin privileges.",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    def resend_verification_code(self, username: str) -> dict:
        """Resends the verification code to the user."""
        try:
            response = self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=username
            )
            return {
                "code_delivery_details": response["CodeDeliveryDetails"]
            }
        except self.client.exceptions.UserNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from e
        except self.client.exceptions.InvalidParameterException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except self.client.exceptions.CodeDeliveryFailureException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification code."
            ) from e
        except self.client.exceptions.LimitExceededException as e:
             raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e


_cognito_auth_instance: Optional[CognitoAuth] = None

def get_cognito_auth() -> CognitoAuth:
    """
    Returns a singleton instance of the CognitoAuth class.
    The instance is created on the first call, not at module import time.
    """
    global _cognito_auth_instance
    if _cognito_auth_instance is None:
        _cognito_auth_instance = CognitoAuth()
    return _cognito_auth_instance



async def get_current_user_with_ngroup(
    # Depends on the renamed get_current_user method
    current_user_claims: Optional[dict] = Depends(get_cognito_auth().get_current_user)
) -> dict:
    """
    Dependency that verifies JWT token, fetches user claims,
    and adds the user's ngroup_id from the database.
    Raises HTTPException if authentication fails or ngroup_id is not found.
    """
    if not current_user_claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}, # Standard header for 401
        )

    try:
        # *** Adapt this key based on your Cognito setup for user's DB ID ***
        
        user_db_id_str = current_user_claims.get('id') # 'sub' is typically the Cognito UUID
        if not user_db_id_str:
             raise ValueError("User ID ('id') missing from token claims.")
        user_db_id = user_db_id_str

    except (KeyError, ValueError, TypeError) as e:
         logger.error(f"Error parsing user ID ('id') from token claims: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user identifier in token.")

    try:
        # Call the utility function to query the database
        ngroup_id = await cueuser.get_user_ngroup_id(user_db_id) # Await the DB call

        if ngroup_id is None:
            logger.error(f"Could not find ngroup association in DB for user ID: {user_db_id}")
            # Use 403 Forbidden as the user is authenticated but lacks necessary setup/permissions
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User NGROUP association not found.")

        # Add the ngroup_id to the claims dictionary
        current_user_claims['ngroup_id'] = ngroup_id # Store as UUID object
        return current_user_claims

    except HTTPException as http_exc: # Re-raise explicit HTTP exceptions
         raise http_exc
    except Exception as e:
        # Catch potential DB errors from the util function
        logger.error(f"Database error fetching ngroup_id for user {user_db_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving user group information.")

