from fastapi import APIRouter, HTTPException, Depends, status, Request
import logging

from utils.upload import ( 
    generate_upload_url,
    confirm_single_file_upload_impl, # New
    get_part_upload_url_impl, 
    start_multipart_upload_impl, 
    complete_multipart_upload_impl, 
    abort_multipart_upload_impl
)
from lambda_utils.type_util.upload import ( # Ensure Confirm models are here
    UploadURLPayload, UploadURLResponse,
    ConfirmSingleUploadPayload, ConfirmSingleUploadResponse
)
from lambda_utils.type_util.upload import (
    MultipartStartRequestPayload, MultipartStartResponsePayload,
    MultipartGetPartUrlRequestPayload, MultipartGetPartUrlResponsePayload,
    MultipartCompleteRequestPayload, MultipartCompleteResponsePayload,
    MultipartAbortRequestPayload
)
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer
from utils.auth import get_current_user_with_ngroup 

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload", 
    tags=["upload"],
)

# --- Single File Upload Endpoints ---
@router.post("/upload_url", response_model=UploadURLResponse)
async def post_upload_url(
    params: UploadURLPayload, 
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup),
):
    """
    Step 1 for Single File Upload: Validates permissions and generates a 
    presigned URL for the client to upload directly to S3.
    Returns the presigned URL details and an s3_key for confirmation.
    """
    try:
        return await generate_upload_url(params, user)
    except HTTPException as e: 
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /upload_url for user {user.get('id') if user else 'Unknown'}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error generating upload URL.")

@router.post("/confirm_single", response_model=ConfirmSingleUploadResponse) # Or just status_code=201
async def post_confirm_single_upload(
    params: ConfirmSingleUploadPayload,
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup),
):
    """
    Step 2 for Single File Upload: Client calls this after successfully uploading 
    the file to S3 using the presigned URL.
    This endpoint creates the file and file_status records in the database.
    """
    try:
        return await confirm_single_file_upload_impl(params, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /confirm_single for user {user.get('id') if user else 'Unknown'}, s3_key {params.s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error confirming upload.")


# --- Multipart Endpoints (Refactored) ---

@router.post("/multipart/start", response_model=MultipartStartResponsePayload)
async def post_multipart_start(
    params: MultipartStartRequestPayload, 
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup)
):
    """
    Step 1 for Multipart Upload: Validates permissions and initiates a 
    multipart upload with S3.
    Returns S3 UploadId and a backend-generated s3_key. 
    No DB records for the file are created at this stage.
    """
    try:
        return await start_multipart_upload_impl(params, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /multipart/start for user {user.get('id')}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error starting multipart upload.")

@router.post("/multipart/get_part_url", response_model=MultipartGetPartUrlResponsePayload)
async def post_multipart_get_part_url(
    params: MultipartGetPartUrlRequestPayload, 
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup)
):
    """
    Step 2 for Multipart Upload: Gets a presigned URL for uploading a specific part.
    """
    try:
        return await get_part_upload_url_impl(params, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /multipart/get_part_url for user {user.get('id')}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error getting part URL.")

@router.post("/multipart/complete", response_model=MultipartCompleteResponsePayload)
async def post_multipart_complete(
    params: MultipartCompleteRequestPayload, 
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup)
):
    """
    Step 3 for Multipart Upload: Client calls this after all parts are uploaded to S3.
    Backend completes the multipart upload with S3.
    If S3 complete is successful, creates file and file_status records in the database.
    """
    try:
        return await complete_multipart_upload_impl(params, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /multipart/complete for user {user.get('id')}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error completing multipart upload.")

@router.post("/multipart/abort", status_code=status.HTTP_204_NO_CONTENT)
async def post_multipart_abort(
    params: MultipartAbortRequestPayload, 
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup)
):
    """
    Aborts an S3 multipart upload. No DB records for the file were created at /start,
    so no file/file_status DB cleanup is needed here.
    """
    try:
        await abort_multipart_upload_impl(params, user)
        return None 
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /multipart/abort for user {user.get('id')}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error aborting multipart upload.")

@router.post("/debug/echo_request_details") # Or use a separate debug router
async def debug_echo_request(request: Request):
    raw_body = await request.body()
    decoded_body_preview = "Could not decode body as UTF-8"
    try:
        decoded_body_preview = raw_body.decode('utf-8')[:500] + ("..." if len(raw_body) > 500 else "")
    except UnicodeDecodeError:
        decoded_body_preview = f"[Binary body of length {len(raw_body)} bytes]"

    response_details = {
        "message": "FastAPI received these request details",
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client_host": request.client.host if request.client else "N/A",
        "body_length": len(raw_body),
        "body_preview_utf8": decoded_body_preview,
    }
    logger.info(f"DEBUG /debug/echo_request_details received: {response_details}")
    return response_details