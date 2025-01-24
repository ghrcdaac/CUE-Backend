from fastapi import APIRouter
from apis.endpoints import upload, auth, egress, ngroup, metrics, cueuser, role

router = APIRouter()

@router.get("")
async def root():
    return {"message": "Hello World - This is CUE API. visit /docs for more info."}

router.include_router(upload.router)
router.include_router(auth.router)
router.include_router(egress.router)
router.include_router(ngroup.router)
router.include_router(metrics.router)
router.include_router(cueuser.router)
router.include_router(role.router)