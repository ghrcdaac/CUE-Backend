# utils/upload.py

import os
import boto3
from botocore.exceptions import ClientError # Import ClientError
from fastapi import HTTPException, status

# Keep existing imports for db, types, etc.
from asyncpg.pool import Pool
from datetime import datetime, timezone
from lambda_utils.database_util.db_util import get_connection_pool
from lambda_utils.database_util import file as file_db
from lambda_utils.database_util import file_status as file_status_db
from lambda_utils.database_util import collection as collection_db

from lambda_utils.type_util.upload import upload_url_pld, upload_url_return
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer
import logging


logger = logging.getLogger(__name__)
S3_BUCKET_NAME = os.environ.get("S3_UPLOAD_BUCKET", "cue-sit-dmz")

# --- S3 Client Initialization ---
# Consider initializing the client once, maybe using Depends or a global variable
# For simplicity, keeping the function for now.
def _get_s3_client():
    # Use environment variables for bucket names too
    # bucket_name = os.environ.get("S3_UPLOAD_BUCKET", "default-bucket-name")
    # Using hardcoded "cue-sit-dmz" as per original code for now
    if os.environ.get("ENV") == "dev":
        # Ensure AWS credentials and region are set correctly for dev
        # Using environment variables is generally preferred over hardcoding in code
        s3Client = boto3.client('s3',
                                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                                region_name=os.environ.get("AWS_REGION", "us-west-2") # Use env var for region
                               )
    else:
        # For non-dev, rely on IAM roles or instance profiles
        s3Client = boto3.client('s3')
    return s3Client

# --- Bucket Name ---
# Define bucket name centrally, preferably from environment variable
S3_BUCKET_NAME = os.environ.get("S3_UPLOAD_BUCKET", "cue-sit-dmz") # Default if not set

# --- Single File Upload URL Generation ---
# (Assuming this function is mostly correct, focusing on multipart)
async def generate_upload_url(params: upload_url_pld, user: CueuserAuthBearer) -> upload_url_return:
    # Existing database logic...
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    file_id = None # Initialize file_id
    try:
        async with conn.transaction():
            # Simplified payload for collection lookup
            collection_payload = (params.collection, user.get('ngroup_id')) # Assuming user is dict-like
            collection_resp = await collection_db.get_collection_by_lookup_from_db(conn, collection_payload)
            if not collection_resp:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Collection not found or access denied")

            collection_id = collection_resp[0][0]

            # Simplified payload for file creation
            file_payload = (
                params.file_name,
                params.file_type,
                user.get('id'), # Assuming user is dict-like
                params.size,
                collection_id,
                False, # Assuming this relates to multipart status
                params.checksum
            )
            file_resp = await file_db.create_file_in_db(conn, file_payload)
            if not file_resp:
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create file record in database")
            file_id = file_resp[0] # Get the generated file ID

            # Simplified payload for file status
            status_payload = (
                file_id,
                datetime.now(timezone.utc),
                'unscanned', # Initial status
                None
            )
            await file_status_db.create_file_status_in_db(conn, status_payload)

    except HTTPException as e:
        raise e # Re-raise HTTP exceptions
    except Exception as e:
        print(f"Database error in generate_upload_url: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interacting with database")
    finally:
        if conn:
            await pool.release(conn)

    if not file_id:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to obtain file ID for S3 key")

    # Generate presigned POST URL using the file_id as the key
    s3Client = _get_s3_client()
    s3_key = str(file_id) # Use the database file ID as the S3 Key

    try:
        # Note: generate_presigned_post is for HTML form uploads.
        # If the client does a direct PUT/POST, generate_presigned_url might be simpler.
        # Assuming presigned POST is required by the client's single_file logic.
        presigned_data = s3Client.generate_presigned_post(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Fields={ # Fields the client's form MUST include
                'x-amz-checksum-sha256': params.checksum,
                'Content-Type': params.file_type # Ensure content type is included
            },
            Conditions=[ # Conditions the upload must satisfy
                {'x-amz-checksum-sha256': params.checksum},
                {'Content-Type': params.file_type},
                ["content-length-range", 0, params.size + 1024] # Allow some tolerance? Or exact size?
            ],
            ExpiresIn=3600 # Increased expiry time (e.g., 1 hour)
        )
        # The client needs both the URL and the required fields
        return upload_url_return(url=presigned_data['url'], fields=presigned_data['fields'])

    except ClientError as e:
        print(f"S3 ClientError generating presigned POST: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error generating upload URL")
    except Exception as e:
        print(f"Unexpected error generating presigned POST: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error generating upload URL")


# --- Multipart Upload Functions ---

async def start_multipart_upload(params: dict, user: CueuserAuthBearer) -> dict:
    """
    Initiates a multipart upload in S3.
    Uses the filename as the S3 key (consider changing this).
    Returns a dictionary containing the upload_id.
    """
    s3Client = _get_s3_client()
    file_name = params.get("file_name")
    # collection = params.get("collection") # Optional: Use for DB logging or key prefix
    # upload_target = params.get("upload_target") # Optional: Use for DB logging or key prefix

    if not file_name:
        raise ValueError("Missing 'file_name' in request body")

    # *** S3 Key Strategy Decision Point ***
    # Using filename directly is risky for collisions.
    # Alternatives:
    # 1. Generate a unique ID (UUID) here.
    # 2. Create a DB record first (like single upload) and use its ID.
    # 3. Use a prefix based on collection/user/date + filename.
    # For now, sticking to original logic:
    s3_key = file_name
    # Consider adding user/collection prefix: s3_key = f"{user.cueusername}/{collection}/{file_name}"

    # TODO: Add database record creation here if needed to track multipart uploads
    # Similar to generate_upload_url, create entries in file and file_status tables.
    # Store the s3_key used.

    try:
        print(f"Starting multipart upload for key: {s3_key} in bucket: {S3_BUCKET_NAME}")
        response = s3Client.create_multipart_upload(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            # ContentType=params.get('file_type', 'application/octet-stream'), # Optional: Set content type
            # ChecksumAlgorithm='SHA256' # Specify if you intend S3 to calculate checksums
        )
        upload_id = response.get('UploadId')
        if not upload_id:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get UploadId from S3")

        print(f"Multipart upload started. Upload ID: {upload_id}")
        # Return only the upload ID as expected by the client
        return {"upload_id": upload_id}

    except ClientError as e:
        print(f"S3 ClientError starting multipart upload: {e}")
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'AccessDenied':
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied to start multipart upload.")
        else:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 error starting multipart upload: {error_code or 'Unknown'}")
    except Exception as e:
        print(f"Unexpected error starting multipart upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error starting multipart upload")


async def get_part_upload_url(params: dict, user: CueuserAuthBearer) -> dict:
    """
    Generates a presigned URL for uploading a single part.
    Returns a dictionary containing the presigned_url.
    """
    s3Client = _get_s3_client()
    file_name = params.get("file_name")
    upload_id = params.get("upload_id")
    part_number_str = params.get("part_number")
    # We still receive content_type, might be useful for logging or other logic
    content_type = params.get("content_type")

    # Validation (keep validation)
    if not file_name:
        logger.warning("get_part_upload_url: Missing 'file_name'")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameter: file_name")
    if not upload_id:
        logger.warning("get_part_upload_url: Missing 'upload_id'")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameter: upload_id")
    if not part_number_str:
        logger.warning("get_part_upload_url: Missing 'part_number'")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameter: part_number")
    if not content_type:
        # Log if missing, but don't necessarily fail if not strictly needed for presigning Params
        logger.warning(f"get_part_upload_url: 'content_type' missing in request for part {part_number_str}.")
        # content_type = 'application/octet-stream' # Assign default if needed elsewhere

    try:
        part_number = int(part_number_str)
        if part_number <= 0:
             raise ValueError("Part number must be a positive integer.")
    except (TypeError, ValueError):
         logger.warning(f"get_part_upload_url: Invalid 'part_number' provided: {part_number_str}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid part_number: {part_number_str}")

    s3_key = file_name

    try:
        logger.info(f"Generating presigned URL for Part {part_number}, Key: {s3_key}, UploadID: {upload_id}") # Removed ContentType from log msg

        # *** CORRECTED: Remove ContentType from Params ***
        presign_params = {
            'Bucket': S3_BUCKET_NAME,
            'Key': s3_key,
            'UploadId': upload_id,
            'PartNumber': part_number,
           
        }
        logger.debug(f"Params for generate_presigned_url: {presign_params}")

        presigned_url = s3Client.generate_presigned_url(
            ClientMethod='upload_part',
            Params=presign_params,
            ExpiresIn=3600,
            HttpMethod='PUT'
        )
        logger.info(f"Successfully generated URL for part {part_number}")
        logger.debug(f"Generated URL (first 100 chars): {presigned_url[:100]}...")
        return {"presigned_url": presigned_url}

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'No message')
        logger.error(f"S3 ClientError generating part URL: Code={error_code}, Message='{error_message}'", exc_info=True)
        if error_code == 'AccessDenied':
             detail = "Permission denied by S3 to generate upload URL for this part. Check IAM permissions (s3:PutObject)."
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        else:
             detail = f"S3 error generating part URL: {error_code}"
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error in get_part_upload_url: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error generating part upload URL.")



async def complete_multipart_upload(params: dict, user: CueuserAuthBearer) -> dict:
    """
    Completes a multipart upload in S3.
    Requires the list of parts with ETags and the final object checksum.
    """
    s3Client = _get_s3_client()
    file_name = params.get("file_name")
    upload_id = params.get("upload_id")
    parts_list = params.get("parts") # This is the list of dicts [{PartNumber, ETag, ChecksumSHA256?}]
    full_checksum = params.get("checksum") # Base64 SHA256 of the full file

    if not all([file_name, upload_id, parts_list, full_checksum]):
        raise ValueError("Missing 'file_name', 'upload_id', 'parts', or 'checksum' in request body")

    if not isinstance(parts_list, list):
         raise ValueError("'parts' must be a list")

    # Use the same S3 key strategy as in start_multipart_upload
    s3_key = file_name

    # Structure for boto3: {'Parts': [{'PartNumber': ..., 'ETag': ...}, ...]}
    # The client sends the ChecksumSHA256 for each part, but complete_multipart_upload
    # primarily cares about PartNumber and ETag. S3 validates parts based on ETags.
    # We need to ensure the ETag doesn't have extra quotes.
    formatted_parts = []
    for part in parts_list:
        if isinstance(part, dict) and 'PartNumber' in part and 'ETag' in part:
            formatted_parts.append({
                'PartNumber': part['PartNumber'],
                'ETag': str(part['ETag']).strip('"') # Ensure ETag is string and strip quotes
            })
        else:
             raise ValueError("Invalid structure in 'parts' list. Each item must be a dict with 'PartNumber' and 'ETag'.")

    multipart_payload = {'Parts': formatted_parts}

    try:
        print(f"Completing multipart upload for Key: {s3_key}, UploadID: {upload_id}")
        print(f"Parts payload: {multipart_payload}") # Log the structure being sent
        print(f"Full file checksum: {full_checksum}")

        response = s3Client.complete_multipart_upload(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            UploadId=upload_id,
            MultipartUpload=multipart_payload,
            # Request S3 to validate the assembled object against the provided checksum
            ChecksumSHA256=full_checksum
        )
        print(f"Multipart upload completed successfully. Response: {response}")

        # TODO: Update database status for the file (e.g., change status from 'uploading' to 'uploaded' or 'pending_scan')
        # You'll need the file_id associated with this upload (requires DB record creation in start_multipart_upload)

        # Return the S3 response (contains ETag, Location, etc.)
        return response

    except ClientError as e:
        print(f"S3 ClientError completing multipart upload: {e}")
        error_code = e.response.get('Error', {}).get('Code')
        # Specific error handling (e.g., InvalidPartOrder, NoSuchUpload)
        if error_code == 'InvalidPart':
             detail = "One or more parts specified were invalid."
        elif error_code == 'InvalidPartOrder':
             detail = "Parts were not specified in ascending order."
        elif error_code == 'NoSuchUpload':
             detail = f"The specified multipart upload ID ({upload_id}) does not exist."
        elif error_code == 'EntityTooSmall':
             detail = "A part size was too small (min 5MB, except last part)."
        elif error_code == 'XAmzContentSHA256Mismatch':
             detail = "The provided final checksum did not match the S3 calculated checksum."
        else:
             detail = f"S3 error completing multipart upload: {error_code or 'Unknown'}"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) # Usually 400 for completion errors
    except Exception as e:
        print(f"Unexpected error completing multipart upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error completing multipart upload")


async def abort_multipart_upload(params: dict, user: CueuserAuthBearer) -> None:
    """
    Aborts an ongoing multipart upload in S3.
    """
    s3Client = _get_s3_client()
    file_name = params.get("file_name")
    upload_id = params.get("upload_id")

    if not all([file_name, upload_id]):
        raise ValueError("Missing 'file_name' or 'upload_id' in request body")

    # Use the same S3 key strategy as in start_multipart_upload
    s3_key = file_name

    try:
        print(f"Aborting multipart upload for Key: {s3_key}, UploadID: {upload_id}")
        s3Client.abort_multipart_upload(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            UploadId=upload_id
        )
        print(f"Multipart upload aborted successfully: {upload_id}")

        # TODO: Update database status for the file (e.g., change status to 'aborted' or 'failed')
        # Requires DB record creation in start_multipart_upload.

        return # No content to return on success (204)

    except ClientError as e:
        print(f"S3 ClientError aborting multipart upload: {e}")
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'NoSuchUpload':
             # If the upload doesn't exist, it's effectively aborted. Maybe log a warning but don't fail.
             print(f"Warning: Multipart upload {upload_id} not found during abort (already completed or aborted?).")
             return # Treat as success from client perspective
        else:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 error aborting multipart upload: {error_code or 'Unknown'}")
    except Exception as e:
        print(f"Unexpected error aborting multipart upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error aborting multipart upload")

