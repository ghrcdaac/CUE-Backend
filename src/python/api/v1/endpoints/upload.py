# ./endpoints/upload.py
from fastapi import APIRouter, HTTPException, Depends, status
import logging

from v1.utils.upload import (
    generate_upload_url,
    confirm_single_file_upload_impl,
    get_part_upload_url_impl,
    start_multipart_upload_impl,
    complete_multipart_upload_impl,
    abort_multipart_upload_impl
)
from lambda_utils.type_util.upload import (
    UploadURLPayload, UploadURLResponse,
    ConfirmSingleUploadPayload, ConfirmSingleUploadResponse,
    MultipartStartRequestPayload, MultipartStartResponsePayload,
    MultipartGetPartUrlRequestPayload, MultipartGetPartUrlResponsePayload,
    MultipartCompleteRequestPayload, MultipartCompleteResponsePayload,
    MultipartAbortRequestPayload
)
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer
from v1.utils.auth import get_current_user_with_ngroup

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
    """
    try:
        return await generate_upload_url(params, user)
    except HTTPException as e:
        # Re-raise known HTTP exceptions from the utility function.
        raise e
    except Exception as e:
        # Catch any other unexpected errors.
        logger.error(f"Unexpected error in /upload_url for user {user.get('id', 'Unknown')}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected internal error occurred: {e}")

@router.post("/confirm_single", response_model=ConfirmSingleUploadResponse)
async def post_confirm_single_upload(
    params: ConfirmSingleUploadPayload,
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup),
):
    """
    Step 2 for Single File Upload: Client calls this after successfully uploading
    the file to S3. This endpoint creates the file and file_status records.
    """
    try:
        return await confirm_single_file_upload_impl(params, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /confirm_single for key {params.s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected internal error occurred: {e}")

# --- Multipart Endpoints ---

@router.post("/multipart/start", response_model=MultipartStartResponsePayload)
async def post_multipart_start(
    params: MultipartStartRequestPayload,
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup)
):
    """
    Step 1 for Multipart Upload: Initiates a multipart upload with S3.
    """
    try:
        return await start_multipart_upload_impl(params, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /multipart/start: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected internal error occurred: {e}")

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
        logger.error(f"Unexpected error in /multipart/get_part_url: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected internal error occurred: {e}")

@router.post("/multipart/complete", response_model=MultipartCompleteResponsePayload)
async def post_multipart_complete(
    params: MultipartCompleteRequestPayload,
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup)
):
    """
    Step 3 for Multipart Upload: Completes the upload with S3 and creates DB records.
    """
    try:
        return await complete_multipart_upload_impl(params, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /multipart/complete: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected internal error occurred: {e}")

@router.post("/multipart/abort", status_code=status.HTTP_204_NO_CONTENT)
async def post_multipart_abort(
    params: MultipartAbortRequestPayload,
    user: CueuserAuthBearer = Depends(get_current_user_with_ngroup)
):
    """
    Aborts an S3 multipart upload.
    """
    try:
        await abort_multipart_upload_impl(params, user)
        # On success, return a 204 No Content response.
        return None
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /multipart/abort: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected internal error occurred: {e}")
