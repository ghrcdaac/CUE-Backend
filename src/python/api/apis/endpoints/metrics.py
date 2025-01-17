from fastapi import APIRouter
from lambda_utils.database_util.db_util import get_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/")
async def metrics_endpoint():
    return get_metrics()