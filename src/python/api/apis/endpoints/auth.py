from fastapi import APIRouter, HTTPException, Depends
from lambda_utils.type_util.auth import RefreshTokenRequest, AuthResponse, TokenVerificationRequest  # Import models
from utils.auth import refresh_token, forgot_password, get_current_user, verify_and_get_user # And functions
from lambda_utils.type_util.cueuser import CueuserReturn

router = APIRouter(prefix="/auth", tags=["auth"])

# Added current user end point
@router.get("/me", response_model=CueuserReturn)
async def get_me(current_user: CueuserReturn = Depends(get_current_user)):
    return current_user

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token_endpoint(request: RefreshTokenRequest):
    try:
        return await refresh_token(request.refresh_token)
    except HTTPException as e: # Catch and re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {e}")

@router.post("/forgot_password")
async def forgot_password_endpoint(username: str):
    try:
        result = await forgot_password(username)
        # Cognito's forgot_password doesn't return sensitive data.  Adapt as needed.
        return {"message": "Password reset initiated. Check your email/SMS for a code."}
    except HTTPException as e:  # Catch HTTP exceptions raised by forgot_password
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forgot password failed: {e}")
    

@router.post("/verify_token", response_model=CueuserReturn)  # Return CueuserReturn
async def verify_token_endpoint(request: TokenVerificationRequest):
    """
    Verifies a JWT and returns the associated user information.
    """
    try:
        user = await verify_and_get_user(request.token)
        return user
    except HTTPException as e:  # Catch and re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token verification failed: {e}")