from fastapi import APIRouter

router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("")
async def root():
    return {"message": "Hello World from upload"}