from fastapi import APIRouter, Depends, HTTPException, status

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import events as event_utils
from v2.type_util.events import FilePayload, FileTransferResponse 

router = APIRouter(prefix="/events", tags=["V2 - Events"])

@router.post("/file_transfer", response_model=FileTransferResponse, dependencies=[Depends(require_privilege("collection:create"))]) 
async def manual_file_transfer(payload: FilePayload, user: AuthUser = Depends(get_current_user)):
    """Trigger manual file transfer for a list of files."""
    try: 
        return await event_utils.trigger_manual_file_transfer(payload, user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))