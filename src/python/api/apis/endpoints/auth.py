from fastapi import APIRouter, HTTPException
from utils.auth import logIn, logOut, refreshToken, pwdResponse
from lambda_utils.type_util.auth import auth_response, login, pwd_response

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(param: login) -> auth_response:
    try:
        return await logIn(param)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500) 

@router.post("/pwd_response")
async def pwd_response(param: pwd_response) -> auth_response:
    try:
        return await pwdResponse(param)
    except Exception:
        raise HTTPException(status_code=500)

@router.get("/logout")
async def logout(username: str) -> bool:
    return await logOut(username)

@router.post("/refresh")
async def refresh(token: str) -> auth_response:
    return await refreshToken(token)