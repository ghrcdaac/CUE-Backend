# File: src/python/api/v2/utils/upload.py

import os
import boto3
from botocore.exceptions import ClientError
from uuid import UUID, uuid4
import structlog

from core.db import get_db_connection
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

async def _validate_upload_permissions(collection_name: str, user: AuthUser):
    """
    V2 helper to validate if a user can upload to a collection.
    This function includes all checks from the original v1 implementation.
    """
    async with get_db_connection() as conn:
        collection = await collection_db.get_collection_by_short_name(conn, collection_name)
        if not collection:
            raise UploadValidationError(f"Collection '{collection_name}' not found.")
        
        if "admin" not in user.roles and str(collection['ngroup_id']) not in user.ngroups:
            raise UploadValidationError("You do not have access to this collection.")

        if not collection['active']:
            raise UploadValidationError(f"Collection '{collection_name}' is not active and cannot accept uploads.")

        provider = await provider_db.get_provider_by_id(conn, collection['provider_id'])
        if not provider:
            raise UploadValidationError(f"Configuration error: Provider for collection '{collection_name}' not found.")
        
        if not provider['can_upload']:
            raise UploadValidationError(f"Provider '{provider['short_name']}' is not configured to allow uploads.")
            
    return collection

# --- Single File Upload Logic ---

async def prepare_single_file_upload(params: PrepareUploadRequest, user: AuthUser) -> dict:
    await _validate_upload_permissions(params.collection_name, user)
    file_id, s3_key = uuid4(), str(uuid4())
    s3_client = _get_s3_client()
    try:
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key, 'ContentType': params.content_type},
            ExpiresIn=PRESIGNED_URL_EXPIRATION
        )
        return {"file_id": file_id, "presigned_url": url, "s3_key": s3_key}
    except ClientError as e:
        logger.error("s3.presigned_url.failed", error=str(e))
        raise S3ClientError("Could not generate upload URL.") from e

# --- CHANGE: Simplified to accept a single payload ---
async def complete_single_file_upload(params: CompleteUploadRequest, user: AuthUser) -> UUID:
    """Creates the file and file_status records atomically after a successful upload."""
    async with get_db_connection() as conn:
        collection = await _validate_upload_permissions(params.collection_name, user)
        async with conn.transaction():
            await file_db.create_file_and_status_records(
                conn=conn, file_id=params.file_id, file_name=params.file_name,
                file_type=params.content_type, user_id=user.id, size_bytes=params.file_size_bytes,
                collection_id=collection['id'], collection_path=params.collection_path, checksum=params.checksum
            )
    logger.info("upload.single.completed", file_id=str(params.file_id))
    return params.file_id

# --- Multipart Upload Logic ---

async def start_multipart_upload(params: MultipartStartRequest, user: AuthUser) -> dict:
    await _validate_upload_permissions(params.collection_name, user)
    file_id, s3_key = uuid4(), str(uuid4())
    s3_client = _get_s3_client()
    try:
        response = s3_client.create_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=s3_key, ContentType=params.content_type,
        )
        return {"file_id": file_id, "s3_key": s3_key, "upload_id": response['UploadId']}
    except ClientError as e:
        logger.error("s3.multipart_start.failed", error=str(e))
        raise S3ClientError("Could not start multipart upload.") from e

async def get_multipart_presigned_url(params: MultipartGetPartUrlRequest) -> dict:
    s3_client = _get_s3_client()
    try:
        url = s3_client.generate_presigned_url(
            'upload_part',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': params.s3_key,
                    'UploadId': params.upload_id, 'PartNumber': params.part_number},
            ExpiresIn=PRESIGNED_URL_EXPIRATION
        )
        return {"presigned_url": url}
    except ClientError as e:
        logger.error("s3.multipart_part_url.failed", error=str(e))
        raise S3ClientError("Could not generate part URL.") from e

async def complete_multipart_upload(params: MultipartCompleteRequest, user: AuthUser) -> UUID:
    s3_client = _get_s3_client()
    file_id = UUID(params.s3_key)
    formatted_parts = [{'PartNumber': part.PartNumber, 'ETag': part.ETag} for part in params.parts]
    
    try:
        s3_client.complete_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=params.s3_key, UploadId=params.upload_id,
            MultipartUpload={'Parts': formatted_parts}
        )
    except ClientError as e:
        logger.error("s3.multipart_complete.failed", error=str(e))
        raise S3ClientError(f"Failed to complete S3 multipart upload: {e.response['Error']['Code']}") from e

    async with get_db_connection() as conn:
        collection = await _validate_upload_permissions(params.collection_name, user)
        async with conn.transaction():
            await file_db.create_file_and_status_records(
                conn=conn, file_id=file_id, file_name=params.file_name,
                file_type=params.content_type, user_id=user.id, size_bytes=params.final_file_size,
                collection_id=collection['id'], collection_path=params.collection_path, checksum=params.checksum
            )
    logger.info("upload.multipart.completed", file_id=str(file_id))
    return file_id

async def abort_multipart_upload(params: MultipartAbortRequest):
    s3_client = _get_s3_client()
    try:
        s3_client.abort_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=params.s3_key, UploadId=params.upload_id
        )
        logger.info("upload.multipart.aborted", s3_key=params.s3_key, upload_id=params.upload_id)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchUpload':
            logger.warning("s3.multipart_abort.not_found", s3_key=params.s3_key)
            return
        logger.error("s3.multipart_abort.failed", error=str(e))
        raise S3ClientError("Failed to abort S3 multipart upload.") from e
