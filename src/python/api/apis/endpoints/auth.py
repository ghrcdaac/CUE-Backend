from fastapi import APIRouter, Depends, HTTPException, Request, status

from lambda_utils.type_util.auth import (
    AuthResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ConfirmForgotPasswordRequest,
    ChangePasswordRequest,
)
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
    try:
        refreshed_tokens = cognito_auth.refresh_tokens(request.refresh_token)
        return refreshed_tokens
    except HTTPException as e:  # Catch HTTPErrors from cognito_auth
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/verify-email")
async def verify_email_route(
    request: Request,
    current_user: dict = Depends(cognito_auth.get_current_user),
    token: str = Depends(bearer_scheme),
):
    """
    Verifies the user's email address in Cognito.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    # Use the access token from the Authorization header
    auth_header = request.headers.get("Authorization")
    access_token = auth_header.split(" ")[1]

    try:
        result = cognito_auth.verify_email(access_token)
        return result
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions from cognito_utils
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/verify-token")
async def verify_token(
    current_user: dict = Depends(cognito_auth.get_current_user),
    token: str = Depends(bearer_scheme),
):
    """
    Verifies the provided access token.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return {"message": "Token is valid", "user": current_user}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Initiates the forgot password flow."""
    try:
        result = cognito_auth.forgot_password(request.username)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.post("/confirm-forgot-password")
async def confirm_forgot_password(request: ConfirmForgotPasswordRequest):
    """Confirms the forgot password flow with the code and new password."""
    try:
        cognito_auth.confirm_forgot_password(
            request.username, request.confirmation_code, request.new_password
        )
        return {"message": "Password successfully reset."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(cognito_auth.get_current_user),
    token: str = Depends(bearer_scheme),
):
    """Changes the user's password (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    # Use the access token from the Authorization header
    auth_header = request.headers.get("Authorization")
    access_token = auth_header.split(" ")[1]
    try:
        cognito_auth.change_password(
            access_token, request.previous_password, request.new_password
        )
        return {"message": "Password successfully changed."}
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions from cognito_utils
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e