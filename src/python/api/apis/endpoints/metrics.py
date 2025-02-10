from fastapi import APIRouter, Depends
from lambda_utils.database_util.db_util import get_metrics, reset_metrics
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user

router = APIRouter(tags=["metrics"])

@router.get("/metrics")
async def metrics_endpoint(user: CueuserAuth = Depends(get_current_user)):
    return await get_metrics()  # Add 'await' here

@router.post("/metrics/reset")
async def reset_metrics_endpoint(user: CueuserAuth = Depends(get_current_user)):
    await reset_metrics()  # Add 'await' here
    return {"message": "Metrics reset successfully"}