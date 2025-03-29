import os
import time
from typing import Optional
import logging 
from uuid import UUID 

import boto3
import requests
from jose import jwk, jwt
from jose.utils import base64url_decode

from fastapi import HTTPException, status, Request, Depends

from utils import cueuser

logger = logging.getLogger(__name__)


class CognitoAuth:

    def __init__(self):
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
            try:
                 response = requests.get(url, timeout=5) # Added timeout
                 response.raise_for_status()
                 self._keys = response.json().get("keys") # Store only keys
                 self._keys_fetched_at = time.time()
                 if not self._keys:
                      logger.error("JWKS keys list is empty or missing.")
                      raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='JWKS key format error')
            except requests.exceptions.RequestException as e:
                 logger.error(f"Error fetching JWKS keys: {e}", exc_info=True)
                 # Keep using stale keys if available and fetch failed recently
                 if self._keys and time.time() - self._keys_fetched_at < 600: # Stale for 10 mins ok
                      logger.warning("Using stale JWKS keys due to fetch error.")
                      return self._keys
                 else:
                      self._keys = None # Force refetch next time if completely failed
                      raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Could not fetch authentication keys') from e
        return self._keys

    async def get_current_user(self, request: Request) -> Optional[dict]: 
        """Verifies the access token from header and returns claims."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("Authorization header missing")
            # Return None, let dependency handle raising 401 if needed by caller
            return None
        try:
            if not auth_header.startswith("Bearer "):
                 raise ValueError("Invalid Authorization header format")
            bearer_token = auth_header.split(" ")[1]
            return self.verify_token(bearer_token) # Verify and return claims
        except ValueError as e:
             logger.warning(f"Auth header error: {e}")
             return None # Treat as unauthenticated
        except HTTPException as e:
             logger.warning(f"Token verification failed: {e.detail}")
             raise e # Re-raise HTTPExceptions from verify_token
        except Exception as e:
            logger.error(f"Unexpected error getting user claims: {e}", exc_info=True)
            return None # Treat as unauthenticated

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

            # Additional check: 'token_use' should be 'access' or 'id'
            token_use = claims.get('token_use')
            if token_use not in ['access', 'id']:
                 logger.warning(f"Invalid token_use: {token_use}")
                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token use')

            logger.info(f"Token verified successfully for user: {claims.get('username') or claims.get('sub')}")
            return claims

        except jwt.ExpiredSignatureError:
            logger.warning("Token is expired (caught by jose).")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token is expired')
        except Exception as e:
            logger.error(f"Error during token claim verification: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token verification failed')

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


_cognito_auth_instance = CognitoAuth()
def get_cognito_auth() -> CognitoAuth:
    """Returns a singleton instance of the CognitoAuth class."""
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
        user_db_id_str = current_user_claims.get('sub') # 'sub' is typically the Cognito UUID
        if not user_db_id_str:
             raise ValueError("User ID ('sub') missing from token claims.")
        user_db_id = UUID(user_db_id_str)

    except (KeyError, ValueError, TypeError) as e:
         logger.error(f"Error parsing user ID ('sub') from token claims: {e}", exc_info=True)
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

