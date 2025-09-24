# ==============================================================================
# File: src/python/api/v2/endpoints/upload.py (Corrected)
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Request
import structlog

from core.security import APIKeyBearer
from v2.type_util.auth import AuthUser
from v2.utils import upload as upload_utils
from v2.type_util.upload import (
    PrepareUploadRequest, PrepareUploadResponse,
    CompleteUploadRequest, UploadSuccessResponse,
    MultipartStartRequest, MultipartStartResponse,
    MultipartGetPartUrlRequest, MultipartGetPartUrlResponse,
    MultipartCompleteRequest, MultipartAbortRequest
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/upload", tags=["V2 - File Upload (CLI)"])

require_upload_key = APIKeyBearer(required_scopes=["file:upload"])

# --- Single File Upload ---

@router.post("/prepare-single", response_model=PrepareUploadResponse)
async def prepare_single_upload(
    request: Request,
    params: PrepareUploadRequest, 
    user: AuthUser = Depends(require_upload_key)
):
    """Step 1 (Single File): Prepare for upload, get a presigned URL."""
    try:
        
        response_data = await upload_utils.prepare_single_file_upload(request, params, user)
        return PrepareUploadResponse(**response_data)
    except (ValueError, upload_utils.UploadValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except upload_utils.S3ClientError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error("endpoint.prepare_single.failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/complete-single", response_model=UploadSuccessResponse)
async def complete_single_upload(
    request: Request,
    params: CompleteUploadRequest,
    user: AuthUser = Depends(require_upload_key)
):
    """Step 2 (Single File): Confirm upload and create database records."""
    try:
        file_id = await upload_utils.complete_single_file_upload(request, params, user)
        return UploadSuccessResponse(
            file_id=file_id, status="unscanned",
            message="Upload confirmed and file is awaiting scan."
        )
    except (ValueError, upload_utils.UploadValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("endpoint.complete_single.failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Multipart Upload ---

@router.post("/multipart/start", response_model=MultipartStartResponse)
async def multipart_start(
    request: Request,
    params: MultipartStartRequest, 
    user: AuthUser = Depends(require_upload_key)
):
    """Step 1 (Multipart): Start a multipart upload."""
    try:
        
        response_data = await upload_utils.start_multipart_upload(request, params, user)
        return MultipartStartResponse(**response_data)
    except (ValueError, upload_utils.UploadValidationError, upload_utils.S3ClientError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("endpoint.multipart_start.failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/multipart/get-part-url", response_model=MultipartGetPartUrlResponse)
async def multipart_get_part_url(
    params: MultipartGetPartUrlRequest, _user: AuthUser = Depends(require_upload_key)
):
    """Step 2 (Multipart): Get a presigned URL for a single part."""
    try:
       
        response_data = await upload_utils.get_multipart_presigned_url(params)
        return MultipartGetPartUrlResponse(**response_data)
    except upload_utils.S3ClientError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/multipart/complete", response_model=UploadSuccessResponse)
async def multipart_complete(
    request: Request,
    params: MultipartCompleteRequest, 
    user: AuthUser = Depends(require_upload_key)
):
    """Step 3 (Multipart): Complete the upload and create DB records."""
    try:
        file_id = await upload_utils.complete_multipart_upload(request, params, user)
        return UploadSuccessResponse(
            file_id=file_id, status="unscanned",
            message="Multipart upload confirmed and file is awaiting scan."
        )
    except (ValueError, upload_utils.UploadValidationError, upload_utils.S3ClientError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("endpoint.multipart_complete.failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/multipart/abort", status_code=status.HTTP_204_NO_CONTENT)
async def multipart_abort(
    params: MultipartAbortRequest, _user: AuthUser = Depends(require_upload_key)
):
    """Abort a multipart upload."""
    try:
        await upload_utils.abort_multipart_upload(params)
    except upload_utils.S3ClientError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))