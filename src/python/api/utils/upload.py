# ./utils/upload.py
import os
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
import logging
from uuid import uuid4, UUID
from datetime import datetime, timezone, timedelta
from typing import Tuple, Dict, Any, Optional

from asyncpg.pool import Pool
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError

from lambda_utils.database_util.db_util import get_connection_pool
from lambda_utils.database_util import (
    collection as collection_db_utils,
    provider as provider_db_utils,
    file as file_db_utils,
    file_status as file_status_db_utils
)
from lambda_utils.type_util.upload import (
    MultipartStartRequestPayload, MultipartStartResponsePayload,
    MultipartGetPartUrlRequestPayload, MultipartGetPartUrlResponsePayload,
    MultipartCompleteRequestPayload, MultipartCompleteResponsePayload,
    MultipartAbortRequestPayload, UploadURLPayload, UploadURLResponse,
    ConfirmSingleUploadPayload, ConfirmSingleUploadResponse
)
from lambda_utils.type_util.collection import CollectionReturn
from lambda_utils.type_util.provider import ProviderReturn
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer

logger = logging.getLogger(__name__)
S3_BUCKET_NAME = os.environ.get("S3_UPLOAD_BUCKET", "cue-uat-dmz")

# --- Helper Functions ---

def _get_s3_client():
    """Initializes and returns a boto3 S3 client based on the environment."""
    if os.environ.get("ENV") == "dev":
        logger.debug("Initializing S3 client for DEV environment.")
        return boto3.client(
            's3',
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "us-west-2")
        )
    logger.debug("Initializing S3 client for non-DEV (IAM role based).")
    return boto3.client('s3')

async def _validate_upload_permissions(
    conn, collection_short_name: str, user: CueuserAuthBearer
) -> Tuple[CollectionReturn, ProviderReturn]:
    """Validates if a user has permission to upload to a given collection."""
    user_id_from_token = user.get('id')
    user_ngroup_id_from_token = user.get('ngroup_id')

    if not user_id_from_token or not user_ngroup_id_from_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User identity or group information missing in auth token.")

    user_ngroup_id_uuid = UUID(str(user_ngroup_id_from_token))
    
    try:
        collection_lookup_params = (collection_short_name, user_ngroup_id_uuid)
        collection_rows = await collection_db_utils.get_collection_by_lookup_from_db(conn, collection_lookup_params)
        if not collection_rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection '{collection_short_name}' not found or you do not have access to it.")
        
        collection_obj = CollectionReturn.from_db_row(collection_rows[0])
        if not collection_obj.active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Collection '{collection_short_name}' is not active and cannot accept uploads.")
        
        provider_rows = await provider_db_utils.get_provider_from_db(conn, (collection_obj.provider_id,))
        if not provider_rows:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Configuration error: Provider for collection '{collection_short_name}' not found.")
        
        provider_obj = ProviderReturn.from_db_row(provider_rows[0])
        if provider_obj.ngroup_id != user_ngroup_id_uuid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Provider and collection group mismatch.")
        if not provider_obj.can_upload:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Provider '{provider_obj.short_name}' is not configured to allow uploads.")

        return collection_obj, provider_obj
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during permission validation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while validating permissions.")

# --- Single File Upload ---

async def generate_upload_url(params: UploadURLPayload, user: CueuserAuthBearer) -> UploadURLResponse:
    """Generates a presigned POST URL for a single file upload."""
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    app_generated_s3_key = str(uuid4())
    try:
        await _validate_upload_permissions(conn, params.collection, user)
    finally:
        if conn: await pool.release(conn)

    s3_client = _get_s3_client()
    try:
        presigned_data = s3_client.generate_presigned_post(
            Bucket=S3_BUCKET_NAME, Key=app_generated_s3_key,
            Fields={'x-amz-checksum-sha256': params.checksum, 'Content-Type': params.file_type},
            Conditions=[
                {'x-amz-checksum-sha256': params.checksum}, {'Content-Type': params.file_type},
                ["content-length-range", 1, params.size + (1024*1024)]
            ],
            ExpiresIn=3600
        )
        return UploadURLResponse(url=presigned_data['url'], fields=presigned_data['fields'], s3_key=app_generated_s3_key)
    except ClientError as e:
        logger.error(f"S3 ClientError generating presigned POST for key {app_generated_s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 Error: {e.response['Error']['Code']}")

async def confirm_single_file_upload_impl(params: ConfirmSingleUploadPayload, user: CueuserAuthBearer) -> ConfirmSingleUploadResponse:
    """Confirms a single file upload by creating database records."""
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    file_id_to_insert = UUID(params.s3_key)
    try:
        collection_obj, _ = await _validate_upload_permissions(conn, params.collection, user)
        
        async with conn.transaction():
            file_create_payload = (
                file_id_to_insert, params.file_name, params.file_type,
                UUID(str(user.get('id'))), params.size_bytes, collection_obj.id,
                params.collection_path, False, params.checksum
            )
            await file_db_utils.create_file_in_db(conn, file_create_payload)
            
            status_payload = (file_id_to_insert, 'unscanned', datetime.now(timezone.utc))
            await file_status_db_utils.upsert_file_status_in_db(conn, status_payload)
        
        logger.info(f"Confirmed single upload. DB File ID & S3 Key: {file_id_to_insert}")
        return ConfirmSingleUploadResponse(file_id=str(file_id_to_insert), status='unscanned')
    except (UniqueViolationError, ForeignKeyViolationError) as e:
        logger.warning(f"Database constraint violation during upload confirmation for key {params.s3_key}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Database constraint failed: {e.detail}")
    except Exception as e:
        logger.error(f"Error in confirm_single_file_upload for S3 key {params.s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during upload confirmation.")
    finally:
        if conn: await pool.release(conn)

# --- Multipart Upload Functions ---

async def start_multipart_upload_impl(params: MultipartStartRequestPayload, user: CueuserAuthBearer) -> MultipartStartResponsePayload:
    """Initiates a multipart upload with S3."""
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    app_generated_s3_key = str(uuid4())
    try:
        await _validate_upload_permissions(conn, params.collection, user)
    finally:
        if conn: await pool.release(conn)
    
    s3_client = _get_s3_client()
    try:
        response = s3_client.create_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=app_generated_s3_key, ContentType=params.content_type,
        )
        s3_upload_id = response.get('UploadId')
        if not s3_upload_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 did not return an UploadId.")
        
        return MultipartStartResponsePayload(upload_id=s3_upload_id, s3_key=app_generated_s3_key)
    except ClientError as e:
        logger.error(f"S3 ClientError starting multipart for key {app_generated_s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 Error: {e.response['Error']['Code']}")

async def get_part_upload_url_impl(params: MultipartGetPartUrlRequestPayload, user: CueuserAuthBearer) -> MultipartGetPartUrlResponsePayload:
    """Gets a presigned URL for a single part of a multipart upload."""
    s3_client = _get_s3_client()
    try:
        presign_params = {
            'Bucket': S3_BUCKET_NAME, 'Key': params.file_name,
            'UploadId': params.upload_id, 'PartNumber': params.part_number,
        }
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='upload_part', Params=presign_params, ExpiresIn=3600, HttpMethod='PUT'
        )
        return MultipartGetPartUrlResponsePayload(presigned_url=presigned_url)
    except ClientError as e:
        logger.error(f"S3 ClientError generating part URL for key {params.file_name}, part {params.part_number}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 Error: {e.response['Error']['Code']}")

async def complete_multipart_upload_impl(params: MultipartCompleteRequestPayload, user: CueuserAuthBearer) -> MultipartCompleteResponsePayload:
    """Completes a multipart upload and creates database records."""
    s3_client = _get_s3_client()
    file_id_for_db_and_s3_key = UUID(params.s3_key)
    formatted_parts = [{'PartNumber': part.PartNumber, 'ETag': str(part.ETag).strip('"')} for part in params.parts]
    
    try:
        logger.info(f"Completing multipart upload with S3 for Key: {str(file_id_for_db_and_s3_key)}")
        s3_response = s3_client.complete_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=str(file_id_for_db_and_s3_key), UploadId=params.upload_id,
            MultipartUpload={'Parts': formatted_parts}, ChecksumSHA256=params.checksum
        )
    except ClientError as e:
        logger.error(f"S3 ClientError completing multipart for key {str(file_id_for_db_and_s3_key)}: {e}", exc_info=True)
        error_code = e.response.get('Error', {}).get('Code')
        detail = f"S3 Error: {error_code}"
        if error_code == 'XAmzContentSHA256Mismatch':
            detail = "Checksum mismatch: The final file checksum did not match the value provided."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    try:
        collection_obj, _ = await _validate_upload_permissions(conn, params.collection, user)
        async with conn.transaction():
            file_create_payload = (
                file_id_for_db_and_s3_key, params.file_name, params.content_type,
                UUID(str(user.get('id'))), params.final_file_size, collection_obj.id,
                params.collection_path, False, params.checksum
            )
            await file_db_utils.create_file_in_db(conn, file_create_payload)
            
            status_payload = (file_id_for_db_and_s3_key, 'unscanned', datetime.now(timezone.utc))
            await file_status_db_utils.upsert_file_status_in_db(conn, status_payload)
        
        final_etag = s3_response.get('ETag','').strip('"')
        return MultipartCompleteResponsePayload(
            Location=s3_response.get('Location', ''), Bucket=s3_response.get('Bucket', S3_BUCKET_NAME),
            Key=s3_response.get('Key', str(file_id_for_db_and_s3_key)), ETag=final_etag
        )
    except (UniqueViolationError, ForeignKeyViolationError) as e:
        logger.warning(f"Database constraint violation during MPU confirmation for key {params.s3_key}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Database constraint failed: {e.detail}")
    except Exception as e:
        logger.error(f"Error in complete_multipart_upload for S3 key {params.s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error confirming multipart upload.")
    finally:
        if conn: await pool.release(conn)

async def abort_multipart_upload_impl(params: MultipartAbortRequestPayload, user: CueuserAuthBearer) -> None:
    """Aborts a multipart upload in S3."""
    s3_client = _get_s3_client()
    try:
        logger.info(f"Aborting multipart with S3 for S3 Key: {params.s3_key}, UploadID: {params.upload_id}")
        s3_client.abort_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=params.s3_key, UploadId=params.upload_id
        )
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'NoSuchUpload':
            logger.info(f"MPU {params.upload_id} not found during abort; treating as success.")
            return
        logger.warning(f"S3 ClientError aborting multipart for key {params.s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 Error: {error_code}")
