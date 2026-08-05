from fastapi import APIRouter
from v2.endpoints import (auth,
     cueuser, ngroup, provider, role, collection, upload, archive, file_metrics, file,
      user_application, api_keys, egress, events
     )

router = APIRouter()

@router.get("")
async def root():
    return {"message": "Hello World - This is CUE API. visit /docs for more info."}

router.include_router(auth.router)
router.include_router(upload.router)
router.include_router(egress.router)
router.include_router(ngroup.router)
# router.include_router(metrics.router)
router.include_router(cueuser.router)
router.include_router(role.router)
# router.include_router(privilege.router)
router.include_router(provider.router)
# router.include_router(cueuser_ngroup.router)
# router.include_router(cueuser_role.router)
# router.include_router(role_privilege.router)
# router.include_router(cueuser_provider.router)
router.include_router(collection.router)
router.include_router(file.router)
# router.include_router(file_status.router)
router.include_router(file_metrics.router)
router.include_router(user_application.router)
# router.include_router(cueuser_auth.router)
router.include_router(archive.router)
router.include_router(api_keys.router)
# router.include_router(oidc_test_helpers.router)
router.include_router(events.router)