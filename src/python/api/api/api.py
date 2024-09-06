from fastapi import APIRouter
from api.endpoints import upload

router = APIRouter()

@router.get("")
async def root():
    return {"message": "Hello World"}

router.include_router(upload.router)