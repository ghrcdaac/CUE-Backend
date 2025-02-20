from fastapi import APIRouter, Depends, HTTPException, status, Body

from lambda_utils.type_util.auth import AuthResponse, RefreshTokenRequest
from utils.cognito_utils import CognitoAuth
from utils.JWTBearer import bearer_scheme

cognito_auth = CognitoAuth()

router = APIRouter()

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refreshes the access and ID tokens using the refresh token.
    """
    refreshed_tokens = cognito_auth.refresh_tokens(request.refresh_token)
    return refreshed_tokens

@router.get("/verify-email")
async def verify_email_route(current_user: dict = Depends(cognito_auth.get_current_user), token:str =  Depends(bearer_scheme)):
    """
    Verifies the user's email address in Cognito.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Use the access token from the Authorization header
    auth_header = request.headers.get("Authorization")
    access_token = auth_header.split(" ")[1]

    result = cognito_auth.verify_email(access_token)
    return result


@router.get("/verify-token")
async def verify_token(current_user: dict = Depends(cognito_auth.get_current_user), token:str =  Depends(bearer_scheme)):
    """
    Verifies the provided access token.
    """
    if current_user:
        return {"message": "Token is valid", "user": current_user}
    else:
         raise HTTPException(status_code=401, detail="Not authenticated")