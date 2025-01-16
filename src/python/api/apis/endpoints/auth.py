from fastapi import APIRouter
from utils.auth import getLoginUrl, getLogoutUrl, refreshToken
from lambda_utils.type_util.auth import auth_token

router = APIRouter(prefix="/auth", tags=["auth"])

router.post("/login")
async def login(state: str) -> auth_token:
    return await getLoginUrl(state)

router.post("/logout")
async def logout(host: str) -> str:
    return await getLogoutUrl(host)

router.post("/refresh")
async def refresh(user_id: str) -> auth_token:
    return await refreshToken(user_id)