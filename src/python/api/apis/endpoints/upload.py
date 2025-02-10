from fastapi import APIRouter, Depends
from utils.upload import generate_upload_url
from lambda_utils.type_util.upload import upload_url_pld, upload_url_return
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user


router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("")
async def root(user: CueuserAuth = Depends(get_current_user)):
    return {"message": f"Hello {user.cueusername} from upload"}

@router.get("/upload_url")
async def upload_url(params:upload_url_pld, user: CueuserAuth = Depends(get_current_user)) -> upload_url_return:
    
    return await generate_upload_url(params)
    