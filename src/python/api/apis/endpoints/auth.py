from fastapi import APIRouter
from utils.auth import logIn, logOut, refreshToken
from lambda_utils.type_util.auth import auth_token, login

router = APIRouter(prefix="/auth", tags=["auth"])

router.post("/login")
async def login(param: login) -> auth_token:
    return await logIn(param)

router.post("/logout")
async def logout(username: str) -> str:
    return await logOut(username)

router.post("/refresh")
async def refresh(token: str) -> auth_token:
    return await refreshToken(token)