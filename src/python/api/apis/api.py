from fastapi import APIRouter
from apis.endpoints import (
     upload, auth, egress, ngroup, metrics, cueuser, role, privilege, provider, cueuser_ngroup,
     cueuser_role, role_privilege, cueuser_provider, collection, file, file_status, user_application, cueuser_auth, file_metrics, archive
     )

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
router.include_router(privilege.router)
router.include_router(provider.router)
router.include_router(cueuser_ngroup.router)
router.include_router(cueuser_role.router)
router.include_router(role_privilege.router)
router.include_router(cueuser_provider.router)
router.include_router(collection.router)
router.include_router(file.router)
router.include_router(file_status.router)
router.include_router(file_metrics.router)
router.include_router(user_application.router)
router.include_router(cueuser_auth.router)
router.include_router(archive.router)