from fastapi import APIRouter
from api.endpoints import upload, auth
from api.endpoints import egress

router = APIRouter()

@router.get("")
async def root():
    return {"message": "Hello World"}

router.include_router(upload.router)
router.include_router(auth.router)
router.include_router(egress.router)