import os
import time
from typing import Optional

import boto3
import requests
from jose import jwk, jwt
from jose.utils import base64url_decode
from fastapi import HTTPException, status, Request


class CognitoAuth:

    def __init__(self):
        self.region = os.environ["AWS_REGION"]
        self.user_pool_id = os.environ["POOL_ID"]
        self.client_id = os.environ["CLIENT_ID"]
        self.client = boto3.client("cognito-idp", region_name=self.region)
        self._keys = None

    def _fetch_keys(self):
        """Fetches and caches Cognito's public keys."""
        if self._keys is None or time.time() - self._keys["fetched_at"] > 3600:
            url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            response = requests.get(url)
            response.raise_for_status()
            self._keys = response.json()
            self._keys["fetched_at"] = time.time()
        return self._keys["keys"]

    async def get_current_user(self, request: Request) -> Optional[dict]:
        """Verifies the access token and retrieves user attributes."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        try:
            bearer_token = auth_header.split(" ")[1]
            return self.verify_token(bearer_token)
        except Exception:
            return None

    def verify_token(self, token: str) -> dict:
        """Verifies a JWT token against the Cognito User Pool."""
        keys = self._fetch_keys()
        headers = jwt.get_unverified_header(token)
        kid = headers['kid']
        key_index = -1
        for i in range(len(keys)):
            if kid == keys[i]['kid']:
                key_index = i
                break
        if key_index == -1:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Public key not found in jwks.json')

        public_key = jwk.construct(keys[key_index])
        message, encoded_signature = str(token).rsplit('.', 1)
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

        if not public_key.verify(message.encode("utf8"), decoded_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Signature verification failed')

        claims = jwt.get_unverified_claims(token)
        if time.time() > claims['exp']:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token is expired')

        audience = claims['aud'] if 'aud' in claims else claims['client_id']
        if audience != self.client_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token was not issued for this app client')
        return claims

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


def get_cognito_auth() -> CognitoAuth:
    return CognitoAuth()