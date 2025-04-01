from fastapi import APIRouter, HTTPException, Depends, status
from utils.upload import generate_upload_url
from lambda_utils.type_util.upload import upload_url_pld, upload_url_return
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer

from utils.auth import get_cognito_auth
from utils.JWTBearer import bearer_scheme


router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("")
async def root(user:CueuserAuthBearer = Depends(get_cognito_auth().get_current_user)):
    return {"message": f"Hello {user.cueusername} from upload"}

@router.post("/upload_url")
async def upload_url(params: upload_url_pld, 
                     user: dict = Depends(get_cognito_auth().get_current_user),
                     token: str = Depends(bearer_scheme)) -> upload_url_return:
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await generate_upload_url(params, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    