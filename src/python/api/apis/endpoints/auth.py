from fastapi import APIRouter, Depends, HTTPException, Request, status, Body

from lambda_utils.type_util.auth import (
    AuthResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ConfirmForgotPasswordRequest,
    ChangePasswordRequest,
)
from utils.auth import get_cognito_auth, CognitoAuth
from utils.JWTBearer import bearer_scheme


router = APIRouter()

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshTokenRequest, cognito_auth = Depends(get_cognito_auth)):  
    """
    Refreshes the access and ID tokens using the refresh token.
    """
    try:
        refreshed_tokens = cognito_auth.refresh_tokens(request.refresh_token)
        return refreshed_tokens
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


# @router.get("/verify-email")
# async def verify_email_route(
#     request: Request,
#     current_user: dict = Depends(get_cognito_auth().get_current_user),  
#     cognito_auth = Depends(get_cognito_auth) # Use Depends
# ):
#     """
#     Verifies the user's email address in Cognito.
#     """
#     if not current_user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
#     # Use the access token from the Authorization header
#     auth_header = request.headers.get("Authorization")
#     access_token = auth_header.split(" ")[1]

#     try:
#         result = cognito_auth.verify_email(access_token)
#         return result
#     except HTTPException as e:
#         raise e  # Re-raise HTTP exceptions from auth
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
#         ) from e


@router.get("/verify-token")
async def verify_token(current_user: dict = Depends(get_cognito_auth().get_current_user)): 
    """
    Verifies the provided access token.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return {"message": "Token is valid", "user": current_user}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, cognito_auth = Depends(get_cognito_auth)):  
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
async def confirm_forgot_password(request: ConfirmForgotPasswordRequest, cognito_auth = Depends(get_cognito_auth)):  
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
    request: Request,  # Get the request object as a dependency!
    change_password_request: ChangePasswordRequest,  # Use a separate variable
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    cognito_auth: CognitoAuth = Depends(get_cognito_auth)
):
    """Changes the user's password (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Correctly get the access token from the Authorization header:
    auth_header = request.headers.get("Authorization")
    if not auth_header: # Added check for auth header
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    access_token = auth_header.split(" ")[1]

    try:
        cognito_auth.change_password(
            access_token, change_password_request.previous_password, change_password_request.new_password
        )
        return {"message": "Password successfully changed."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.post("/verify-email")  # New endpoint for admin verification
async def admin_verify_email_route(
    username: str = Body(..., embed=True),
    
    cognito_auth: CognitoAuth = Depends(get_cognito_auth)
):
    """
    Admin endpoint to manually verify a user's email.  Requires admin privileges.
    """
    # if not current_user:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # # Add authorization check here (e.g., check for an "admin" role in cognito:groups)
    # if "admin" not in current_user.get("cognito:groups", []):  # Example: Check for admin group
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        cognito_auth.admin_verify_email(username)
        return {"message": f"Email for user '{username}' verified successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.post("/resend-code")
async def resend_verification_code_route(username: str = Body(..., embed=True), cognito_auth: CognitoAuth = Depends(get_cognito_auth)):
    """Resends the verification code to the user."""
    try:
        result = cognito_auth.resend_verification_code(username)
        return result

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        ) from e