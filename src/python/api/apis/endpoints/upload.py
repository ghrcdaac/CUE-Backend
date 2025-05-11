# main.py (or wherever your router is defined)

from fastapi import APIRouter, HTTPException, Depends, status, Body # Added Body
from typing import Dict, List, Any # For type hinting dict bodies

# Import your existing utils and auth functions
from utils.upload import (
    generate_upload_url,
    get_part_upload_url,
    start_multipart_upload,
    complete_multipart_upload,
    abort_multipart_upload # Import the new abort function
)
from lambda_utils.type_util.upload import upload_url_pld, upload_url_return
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer

from utils.auth import get_cognito_auth
from utils.JWTBearer import bearer_scheme



router = APIRouter(
    prefix="/upload",
    tags=["upload"],

)


@router.get("")
async def root(user: CueuserAuthBearer = Depends(get_cognito_auth().get_current_user)):
    # This endpoint already has authentication
    return {"message": f"Hello {user.cueusername} from upload"}

# Single file upload URL endpoint (Assuming it's correct)
@router.post("/upload_url", response_model=upload_url_return) # Added response_model for clarity
async def upload_url(
    params: upload_url_pld,
    user: CueuserAuthBearer = Depends(get_cognito_auth().get_current_user),
    # token: str = Depends(bearer_scheme) # Token likely handled within get_current_user
):
    # No need to check 'if not user', Depends handles unauthorized access
    try:
        # Pass the user object/dict directly if needed by generate_upload_url
        return await generate_upload_url(params, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e: # Catch existing HTTPExceptions
        raise e
    except Exception as e:
        # Log the exception for debugging
        print(f"Error in /upload_url: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error generating upload URL.")


# --- Multipart Endpoints ---

# Define expected body structures using Body(...) or Pydantic models for better validation
# Using Dict for now as requested, but Pydantic is recommended

@router.post("/multipart/start", response_model=Dict[str, str]) # Expecting {"upload_id": "..."}
async def multipart_start(
    # Use Body to explicitly define the expected JSON body structure
    params: Dict[str, Any] = Body(..., example={"file_name": "large_file.dat", "collection": "my_collection", "upload_target": "path/to/target"}),
    user: CueuserAuthBearer = Depends(get_cognito_auth().get_current_user) # Added Authentication
):
    """
    Start a multipart upload. Requires authentication.
    Expects JSON body with 'file_name'.
    """
    try:
        # Pass user if needed by start_multipart_upload
        return await start_multipart_upload(params, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e: # Catch existing HTTPExceptions
        raise e
    except Exception as e:
        print(f"Error in /multipart/start: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error starting multipart upload.")


@router.post("/multipart/get_part_url", response_model=Dict[str, str]) # Expecting {"presigned_url": "..."}
async def multipart_get_part_url(
    params: Dict[str, Any] = Body(..., example={"file_name": "large_file.dat", "upload_id": "some_id", "part_number": 1, "checksum": "part_hash_b64"}),
    user: CueuserAuthBearer = Depends(get_cognito_auth().get_current_user) # Added Authentication
):
    """
    Get a presigned URL for uploading a specific part. Requires authentication.
    Expects JSON body with 'file_name', 'upload_id', 'part_number'.
    """
    try:
        # Pass user if needed by get_part_upload_url
        return await get_part_upload_url(params, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e: # Catch existing HTTPExceptions
        raise e
    except Exception as e:
        print(f"Error in /multipart/get_part_url: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error getting part URL.")


@router.post("/multipart/complete") # Response model can be more specific if needed
async def multipart_complete(
    params: Dict[str, Any] = Body(..., example={"file_name": "large_file.dat", "upload_id": "some_id", "parts": [{"PartNumber": 1, "ETag": "etag1"}], "checksum": "full_file_hash_b64"}),
    user: CueuserAuthBearer = Depends(get_cognito_auth().get_current_user) # Added Authentication
):
    """
    Complete a multipart upload. Requires authentication.
    Expects JSON body with 'file_name', 'upload_id', 'parts' (list of dicts), 'checksum'.
    """
    try:
        # Pass user if needed by complete_multipart_upload
        return await complete_multipart_upload(params, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e: # Catch existing HTTPExceptions
        raise e
    except Exception as e:
        print(f"Error in /multipart/complete: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error completing multipart upload.")


@router.post("/multipart/abort", status_code=status.HTTP_204_NO_CONTENT) # No content on successful abort
async def multipart_abort(
    params: Dict[str, Any] = Body(..., example={"file_name": "large_file.dat", "upload_id": "some_id"}),
    user: CueuserAuthBearer = Depends(get_cognito_auth().get_current_user) # Added Authentication
):
    """
    Abort a multipart upload. Requires authentication.
    Expects JSON body with 'file_name', 'upload_id'.
    """
    try:
        # Pass user if needed by abort_multipart_upload
        await abort_multipart_upload(params, user)
        return # Return None for 204 response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e: # Catch existing HTTPExceptions
        raise e
    except Exception as e:
        print(f"Error in /multipart/abort: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error aborting multipart upload.")

