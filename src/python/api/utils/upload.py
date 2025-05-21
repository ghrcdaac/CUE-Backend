import os
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
import logging
from uuid import uuid4, UUID
from datetime import datetime, timezone, timedelta 
from typing import Tuple, Dict, Any, Optional 
from pathlib import Path 

from asyncpg.pool import Pool # type: ignore

from lambda_utils.database_util.db_util import get_connection_pool
from lambda_utils.database_util import collection as collection_db_utils
from lambda_utils.database_util import provider as provider_db_utils
from lambda_utils.database_util import file as file_db_utils
from lambda_utils.database_util import file_status as file_status_db_utils

from lambda_utils.type_util.upload import (
    MultipartStartRequestPayload, MultipartStartResponsePayload,
    MultipartGetPartUrlRequestPayload, MultipartGetPartUrlResponsePayload,
    MultipartCompleteRequestPayload, MultipartCompleteResponsePayload,
    MultipartAbortRequestPayload
)
from lambda_utils.type_util.upload import ( 
    UploadURLPayload, UploadURLResponse,
    ConfirmSingleUploadPayload, ConfirmSingleUploadResponse
)
from lambda_utils.type_util.collection import CollectionReturn
from lambda_utils.type_util.provider import ProviderReturn
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer

logger = logging.getLogger(__name__)
S3_BUCKET_NAME = os.environ.get("S3_UPLOAD_BUCKET", "cue-sit-dmz")

_permission_cache: Dict[Tuple[str, str], Tuple[CollectionReturn, ProviderReturn, datetime]] = {}
PERMISSION_CACHE_TTL_SECONDS = 300  

def _get_s3_client():
    # ... (same as before) ...
    if os.environ.get("ENV") == "dev":
        logger.debug("Initializing S3 client for DEV environment.") 
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "us-west-2")
        )
    else:
        logger.debug("Initializing S3 client for non-DEV (IAM role based).") 
        s3_client = boto3.client('s3')
    return s3_client

async def _validate_upload_permissions(
    conn, collection_short_name: str, user: CueuserAuthBearer
) -> Tuple[CollectionReturn, ProviderReturn]:
    # ... (same as backend_utils_upload_py_v5) ...
    user_id_from_token = user.get('id')
    user_ngroup_id_from_token = user.get('ngroup_id')

    if not user_id_from_token or not user_ngroup_id_from_token:
        logger.error(f"User {user_id_from_token} missing id or ngroup_id in token/claims.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User identity or group information missing.")

    user_ngroup_id_str = str(user_ngroup_id_from_token)
    cache_key = (user_ngroup_id_str, collection_short_name)
    
    cached_entry = _permission_cache.get(cache_key)
    if cached_entry:
        collection_obj_cached, provider_obj_cached, cached_time = cached_entry
        if datetime.now(timezone.utc) - cached_time < timedelta(seconds=PERMISSION_CACHE_TTL_SECONDS):
            logger.info(f"Using cached permissions for user_ngroup '{user_ngroup_id_str}', collection '{collection_short_name}'.")
            return collection_obj_cached, provider_obj_cached
        else:
            logger.info(f"Cached permissions expired for '{cache_key}'. Re-fetching.")
            _permission_cache.pop(cache_key, None)

    logger.info(f"Validating permissions from DB for user_ngroup '{user_ngroup_id_str}', collection '{collection_short_name}'.")
    user_ngroup_id_uuid = UUID(user_ngroup_id_str)

    collection_lookup_params = (collection_short_name, user_ngroup_id_uuid)
    collection_rows = await collection_db_utils.get_collection_by_lookup_from_db(conn, collection_lookup_params)
    if not collection_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection '{collection_short_name}' not found or not accessible.")
    collection_obj = CollectionReturn.from_db_row(collection_rows[0])

    if not collection_obj.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Collection '{collection_short_name}' is not active.")

    provider_rows = await provider_db_utils.get_provider_from_db(conn, (collection_obj.provider_id,))
    if not provider_rows:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Provider config error for coll '{collection_short_name}'.")
    provider_obj = ProviderReturn.from_db_row(provider_rows[0])

    if provider_obj.ngroup_id != user_ngroup_id_uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Provider config mismatch for coll '{collection_short_name}'.")

    if not provider_obj.can_upload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Provider '{provider_obj.short_name}' for coll '{collection_short_name}' cannot upload.")

    _permission_cache[cache_key] = (collection_obj, provider_obj, datetime.now(timezone.utc))
    return collection_obj, provider_obj

# --- Single File Upload ---
async def generate_upload_url(params: UploadURLPayload, user: CueuserAuthBearer) -> UploadURLResponse:
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    # Backend generates the UUID which will be the file.id AND the S3 object key.
    app_generated_file_id_and_s3_key = str(uuid4())
    try:
        await _validate_upload_permissions(conn, params.collection, user)
        logger.info(f"Permissions validated for single upload. App-generated File ID/S3 Key: {app_generated_file_id_and_s3_key}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during permission validation for single upload: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error validating upload permissions.")
    finally:
        if conn: await pool.release(conn)

    s3_client = _get_s3_client()
    try:
        presigned_data = s3_client.generate_presigned_post(
            Bucket=S3_BUCKET_NAME, Key=app_generated_file_id_and_s3_key,
            Fields={'x-amz-checksum-sha256': params.checksum, 'Content-Type': params.file_type},
            Conditions=[
                {'x-amz-checksum-sha256': params.checksum}, {'Content-Type': params.file_type},
                ["content-length-range", 0 if params.size == 0 else 1, params.size + (1024*1024)]
            ],
            ExpiresIn=3600 
        )
        # Return the app_generated_file_id_and_s3_key as s3_key
        return UploadURLResponse(url=presigned_data['url'], fields=presigned_data['fields'], s3_key=app_generated_file_id_and_s3_key)
    except ClientError as e:
        logger.error(f"S3 ClientError (presigned POST, key: {app_generated_file_id_and_s3_key}): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error generating S3 upload URL")

async def confirm_single_file_upload_impl(params: ConfirmSingleUploadPayload, user: CueuserAuthBearer) -> ConfirmSingleUploadResponse:
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    # params.s3_key is the app-generated UUID from generate_upload_url, to be used as file.id
    file_id_to_insert = UUID(params.s3_key) 
    try:
        collection_obj, _ = await _validate_upload_permissions(conn, params.collection, user)
        
        async with conn.transaction(): # type: ignore
            # file_db_utils.create_file_in_db now needs to accept 8 params:
            # (id, name, type, cueuser_id, size, coll_id, coll_path, edpub, checksum)
            # Note: The DDL for file.id should be `id UUID NOT NULL PRIMARY KEY` (no default)
            file_create_payload = (
                file_id_to_insert,      # id (the S3 key, which is our app-generated UUID)
                params.file_name,       # name
                params.file_type,       # type
                UUID(str(user.get('id'))), # cueuser_uploaded
                params.size_bytes,      # size_bytes
                collection_obj.id,      # collection_id
                params.collection_path, # collection_path
                False,                  # edpub (default)
                params.checksum         # checksum
            )
            # This assumes your file_db_utils.create_file_in_db is updated to take these 9 params
            # and inserts the provided ID.
            file_record = await file_db_utils.create_file_in_db(conn, file_create_payload)
            if not file_record or file_record.get('id') != file_id_to_insert:
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create file record with specified ID upon confirmation.")
            
            status_payload = (
                file_id_to_insert, 'unscanned', None, 
                datetime.now(timezone.utc), None, None
            )
            await file_status_db_utils.create_file_status_in_db(conn, status_payload) # type: ignore
            logger.info(f"Confirmed single upload. DB File ID & S3 Key: {file_id_to_insert}")
            return ConfirmSingleUploadResponse(file_id=str(file_id_to_insert), status='unscanned')

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in confirm_single_file_upload for S3 key {params.s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error confirming single file upload.")
    finally:
        if conn: await pool.release(conn)


# --- Multipart Upload Functions ---
async def start_multipart_upload_impl(params: MultipartStartRequestPayload, user: CueuserAuthBearer) -> MultipartStartResponsePayload:
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    # Backend generates the UUID which will be the file.id AND the S3 object key.
    app_generated_file_id_and_s3_key = str(uuid4())
    s3_upload_id: Optional[str] = None
    try:
        await _validate_upload_permissions(conn, params.collection, user)
        logger.info(f"Permissions validated for multipart start. App-generated File ID/S3 Key: {app_generated_file_id_and_s3_key}")
    except HTTPException:
        if conn: await pool.release(conn)
        raise
    except Exception as e:
        logger.error(f"Error during permission validation for multipart start: {e}", exc_info=True)
        if conn: await pool.release(conn)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error validating upload permissions.")
    finally: 
        if conn: await pool.release(conn)

    s3_client = _get_s3_client()
    try:
        logger.info(f"Starting multipart upload with S3 for S3 key: {app_generated_file_id_and_s3_key}")
        response = s3_client.create_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=app_generated_file_id_and_s3_key, ContentType=params.content_type,
        )
        s3_upload_id = response.get('UploadId')
        if not s3_upload_id:
            logger.error(f"Failed to get UploadId from S3 for key {app_generated_file_id_and_s3_key}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get UploadId from S3")
        
        logger.info(f"Multipart initiated with S3. S3 Upload ID: {s3_upload_id}, S3 Key: {app_generated_file_id_and_s3_key}")
        return MultipartStartResponsePayload(upload_id=s3_upload_id, s3_key=app_generated_file_id_and_s3_key)

    except ClientError as e:
        logger.error(f"S3 ClientError starting multipart for key {app_generated_file_id_and_s3_key}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 error starting multipart upload")


async def get_part_upload_url_impl(params: MultipartGetPartUrlRequestPayload, user: CueuserAuthBearer) -> MultipartGetPartUrlResponsePayload:
    s3_client = _get_s3_client()
    # params.file_name from client is the s3_key (our app_generated_file_id_and_s3_key)
    s3_object_key = params.file_name 
    try:
        logger.debug(f"Generating presigned URL for Part {params.part_number}, S3 Key: {s3_object_key}, S3 UploadID: {params.upload_id}")
        presign_params = {
            'Bucket': S3_BUCKET_NAME, 'Key': s3_object_key,
            'UploadId': params.upload_id, 'PartNumber': params.part_number,
        }
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='upload_part', Params=presign_params, ExpiresIn=3600, HttpMethod='PUT'
        )
        logger.debug(f"Successfully generated URL for part {params.part_number}")
        return MultipartGetPartUrlResponsePayload(presigned_url=presigned_url)
    except ClientError as e:
        logger.error(f"S3 ClientError (part URL, key {s3_object_key}, part {params.part_number}): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 error generating part upload URL")


async def complete_multipart_upload_impl(params: MultipartCompleteRequestPayload, user: CueuserAuthBearer) -> MultipartCompleteResponsePayload:
    s3_client = _get_s3_client()
    # params.s3_key is the app-generated UUID from /start, which will be the file.id
    file_id_for_db_and_s3_key = UUID(params.s3_key) 
    
    formatted_parts = [{'PartNumber': part.PartNumber, 'ETag': str(part.ETag).strip('"')} for part in params.parts]
    multipart_payload = {'Parts': formatted_parts}
    s3_response_dict: Dict[str, Any] = {} 

    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    try:
        logger.info(f"Attempting to complete multipart upload with S3 for Key: {str(file_id_for_db_and_s3_key)}, S3 UploadID: {params.upload_id}")
        s3_response = s3_client.complete_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=str(file_id_for_db_and_s3_key), UploadId=params.upload_id,
            MultipartUpload=multipart_payload, ChecksumSHA256=params.checksum
        )
        s3_response_dict = s3_response 
        final_etag = s3_response_dict.get('ETag','').strip('"')
        logger.info(f"S3 Multipart upload completed successfully for S3 key {str(file_id_for_db_and_s3_key)}. S3 ETag: {final_etag}")

        collection_obj, _ = await _validate_upload_permissions(conn, params.collection, user)

        async with conn.transaction(): # type: ignore
            # file_db_utils.create_file_in_db now needs to accept 9 params:
            # (id, name, type, cueuser_id, size, coll_id, coll_path, edpub, checksum)
            file_create_payload = (
                file_id_for_db_and_s3_key, # Use the app-generated UUID as the file.id
                params.file_name,       # Original local filename for 'name' column
                params.content_type,    # Original content_type
                UUID(str(user.get('id'))), # cueuser_uploaded
                params.final_file_size, # size_bytes
                collection_obj.id,      # collection_id
                params.collection_path, # User's target sub-path
                False,                  # edpub (default)
                params.checksum         # overall_checksum
            )
            file_record = await file_db_utils.create_file_in_db(conn, file_create_payload)
            if not file_record or file_record.get('id') != file_id_for_db_and_s3_key:
                logger.critical(f"CRITICAL: S3 MPU complete for {str(file_id_for_db_and_s3_key)}, but DB file record creation/match failed.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File uploaded to S3, but failed to record in database with correct ID. Please contact support.")
            
            status_payload = (
                file_id_for_db_and_s3_key, 'unscanned', None, 
                datetime.now(timezone.utc), None, None
            )
            await file_status_db_utils.create_file_status_in_db(conn, status_payload) # type: ignore
            logger.info(f"DB records created for file {str(file_id_for_db_and_s3_key)} with status 'unscanned'.")
        
        return MultipartCompleteResponsePayload(
            Location=s3_response_dict.get('Location', ''), Bucket=s3_response_dict.get('Bucket', S3_BUCKET_NAME),
            Key=s3_response_dict.get('Key', str(file_id_for_db_and_s3_key)), ETag=final_etag
        )
    except ClientError as e:
        logger.error(f"S3 ClientError (complete multipart, key {str(file_id_for_db_and_s3_key)}): {e}", exc_info=True)
        error_code = e.response.get('Error', {}).get('Code')
        detail = f"S3 error completing multipart: {error_code or 'Unknown'}"
        if error_code == 'XAmzContentSHA256Mismatch':
            detail = "Final file checksum (SHA256) mismatch with S3."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except HTTPException: 
        raise
    except Exception as e: 
        logger.error(f"Error during complete_multipart_upload_impl for S3 key {str(file_id_for_db_and_s3_key)}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error completing upload.")
    finally:
        if conn: await pool.release(conn)


async def abort_multipart_upload_impl(params: MultipartAbortRequestPayload, user: CueuserAuthBearer) -> None:
    s3_client = _get_s3_client()
    # params.s3_key is the app-generated UUID from /start
    s3_object_key_to_abort = params.s3_key 
    
    # No DB records were created at /start for the file in this transactional model,
    # so no DB cleanup is needed here for the file or file_status table.
    try:
        logger.info(f"Aborting multipart with S3 for S3 Key: {s3_object_key_to_abort}, S3 UploadID: {params.upload_id}")
        s3_client.abort_multipart_upload(
            Bucket=S3_BUCKET_NAME, Key=s3_object_key_to_abort, UploadId=params.upload_id
        )
        logger.info(f"Multipart aborted with S3 for S3 key {s3_object_key_to_abort}, Upload ID: {params.upload_id}")
    except ClientError as e:
        logger.warning(f"S3 ClientError (abort multipart, key {s3_object_key_to_abort}): {e}", exc_info=True)
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'NoSuchUpload':
            logger.info(f"MPU {params.upload_id} not found during S3 abort. Treating as effectively aborted.")
            return 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 error aborting: {error_code or 'Unknown'}")
