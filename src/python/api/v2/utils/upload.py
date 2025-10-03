# ==============================================================================
# File: src/python/api/v2/utils/upload.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
import os
import boto3
from botocore.exceptions import ClientError
from uuid import UUID, uuid4
import structlog
from fastapi import Request

from v2.database_util import collection as collection_db
from v2.database_util import provider as provider_db
from v2.database_util import file as file_db
from v2.type_util.auth import AuthUser
from v2.type_util.upload import (
    PrepareUploadRequest, CompleteUploadRequest,
    MultipartStartRequest, MultipartCompleteRequest,
    MultipartGetPartUrlRequest, MultipartAbortRequest
)

logger = structlog.get_logger(__name__)
S3_BUCKET_NAME = os.environ.get("S3_UPLOAD_BUCKET", "cue-uat-dmz")
PRESIGNED_URL_EXPIRATION = 3600  # 1 hour

class S3ClientError(Exception): pass
class UploadValidationError(Exception): pass

def _get_s3_client():
    return boto3.client('s3', region_name=os.environ.get("AWS_REGION", "us-west-2"))

async def _validate_upload_permissions(request: Request, collection_name: str, user: AuthUser):
    """V2 helper to validate if a user can upload to a collection, with detailed error reasons."""
    async with request.state.pool.acquire() as conn:
        collection = await collection_db.get_collection_by_short_name(conn, collection_name)
        if not collection:
            raise UploadValidationError(f"Upload Denied: Collection '{collection_name}' does not exist.")
        
        # Admins have universal access and bypass group/provider checks.
        if "admin" in user.roles:
            return collection
            
        # Check 1: User's group permissions
        user_ngroup_ids = set()
        if user.ngroups:
            # This handles both list-of-dicts and list-of-strings for ngroups
            if isinstance(user.ngroups[0], dict):
                user_ngroup_ids = {str(ng['id']) for ng in user.ngroups}
            else:
                user_ngroup_ids = {str(ng) for ng in user.ngroups}
        
        if str(collection['ngroup_id']) not in user_ngroup_ids:
            raise UploadValidationError(f"Upload Denied: Your API key is not authorized for the DAAC group associated with collection '{collection_name}'.")

        # Check 2: Collection status
        if not collection['active']:
            raise UploadValidationError(f"Upload Denied: Collection '{collection_name}' is inactive and cannot accept new files.")

        # Check 3: Provider status
        provider = await provider_db.get_provider_by_id(conn, collection['provider_id'])
        if not provider:
            # This is an internal configuration error, not a user permission issue.
            raise UploadValidationError(f"Upload Configuration Error: The provider associated with collection '{collection_name}' could not be found.")
        
        if not provider['can_upload']:
            raise UploadValidationError(f"Upload Denied: The provider '{provider['short_name']}' for collection '{collection_name}' is not configured to allow uploads.")
            
    return collection

# --- Single File Upload Logic ---

async def prepare_single_file_upload(request: Request, params: PrepareUploadRequest, user: AuthUser) -> dict:
    collection = await _validate_upload_permissions(request, params.collection_name, user)
    file_id = uuid4()
    
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            await file_db.create_preliminary_file_records(conn, file_id, user.id, collection['id'])

    s3_client = _get_s3_client()
    try:
        url = s3_client.generate_presigned_url('put_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': str(file_id), 'ContentType': params.content_type}, ExpiresIn=PRESIGNED_URL_EXPIRATION)
        return {"file_id": file_id, "presigned_url": url}
    except ClientError as e:
        logger.error("s3.presigned_url.failed", error=str(e))
        raise S3ClientError("Could not generate upload URL.") from e

async def complete_single_file_upload(request: Request, params: CompleteUploadRequest, user: AuthUser) -> UUID:
    async with request.state.pool.acquire() as conn:
        ip_address = {"ip_address": request.client.host}
        collection = await _validate_upload_permissions(request, params.collection_name, user)
        async with conn.transaction():
            await file_db.update_final_file_details(
                conn=conn, file_id=params.file_id, file_name=params.file_name,
                file_type=params.content_type, size_bytes=params.file_size_bytes,
                collection_path=params.collection_path, checksum=params.checksum,
                ip_address=ip_address
            )
    logger.info("upload.single.completed", file_id=str(params.file_id))
    return params.file_id

# --- Multipart Upload Logic ---

async def start_multipart_upload(request: Request, params: MultipartStartRequest, user: AuthUser) -> dict:
    collection = await _validate_upload_permissions(request, params.collection_name, user)
    file_id = uuid4()

    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            await file_db.create_preliminary_file_records(conn, file_id, user.id, collection['id'])

    s3_client = _get_s3_client()
    try:
        response = s3_client.create_multipart_upload(Bucket=S3_BUCKET_NAME, Key=str(file_id), ContentType=params.content_type)
        return {"file_id": file_id, "upload_id": response['UploadId']}
    except ClientError as e:
        logger.error("s3.multipart_start.failed", error=str(e))
        raise S3ClientError("Could not start multipart upload.") from e

async def get_multipart_presigned_url(params: MultipartGetPartUrlRequest) -> dict:
    s3_client = _get_s3_client()
    try:
        url = s3_client.generate_presigned_url(
            'upload_part',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': str(params.file_id),
                    'UploadId': params.upload_id, 'PartNumber': params.part_number},
            ExpiresIn=PRESIGNED_URL_EXPIRATION
        )
        return {"presigned_url": url}
    except ClientError as e:
        logger.error("s3.multipart_part_url.failed", error=str(e))
        raise S3ClientError("Could not generate part URL.") from e

async def complete_multipart_upload(request: Request, params: MultipartCompleteRequest, user: AuthUser) -> UUID:
    s3_client = _get_s3_client()
    file_id = params.file_id
    formatted_parts = [{'PartNumber': part.PartNumber, 'ETag': part.ETag} for part in params.parts]
    ip_address = {"ip_address": request.client.host}
    
    try:
        s3_client.complete_multipart_upload(Bucket=S3_BUCKET_NAME, Key=str(file_id), UploadId=params.upload_id, MultipartUpload={'Parts': formatted_parts})
    except ClientError as e:
        raise S3ClientError(f"Failed to complete S3 multipart upload: {e.response['Error']['Code']}") from e

    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            await file_db.update_final_file_details(
                conn=conn, file_id=file_id, file_name=params.file_name,
                file_type=params.content_type, size_bytes=params.final_file_size,
                collection_path=params.collection_path, checksum=params.checksum,
                ip_address=ip_address
            )
    logger.info("upload.multipart.completed", file_id=str(file_id))
    return file_id

async def abort_multipart_upload(params: MultipartAbortRequest):
    s3_client = _get_s3_client()
    try:
        s3_client.abort_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=str(params.file_id), UploadId=params.upload_id
        )
        logger.info("upload.multipart.aborted", file_id=str(params.file_id), upload_id=params.upload_id)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchUpload':
            logger.warning("s3.multipart_abort.not_found", file_id=str(params.file_id))
            return
        logger.error("s3.multipart_abort.failed", error=str(e))
        raise S3ClientError("Failed to abort S3 multipart upload.") from e
