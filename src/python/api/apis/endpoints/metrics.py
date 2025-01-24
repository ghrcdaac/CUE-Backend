from fastapi import APIRouter
from lambda_utils.database_util.db_util import get_metrics, reset_metrics

router = APIRouter(tags=["metrics"])

@router.get("/metrics")
async def metrics_endpoint():
    return await get_metrics()  # Add 'await' here

@router.post("/metrics/reset")
async def reset_metrics_endpoint():
    await reset_metrics()  # Add 'await' here
    return {"message": "Metrics reset successfully"}