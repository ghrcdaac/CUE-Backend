from fastapi import APIRouter
from utils.upload import generate_upload_url
from lambda_utils.type_util.upload import upload_url_pld, upload_url_return


router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("")
async def root():
    return {"message": "Hello World from upload"}

@router.get("/upload_url")
async def upload_url(params:upload_url_pld) -> upload_url_return:
    
    return await generate_upload_url(params)
    