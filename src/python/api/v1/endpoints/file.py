# endpoints/file.py

from fastapi import APIRouter, HTTPException, Query, Depends
from uuid import UUID
from typing import List, Optional
import logging

# --- Import Authentication ---
# Import the NEW dependency function
from v1.utils.auth import get_current_user_with_ngroup, get_cognito_auth # Keep old one if needed elsewhere

# --- Import utils and types ---
from v1.utils.file import (create_file, get_file, update_file,
                        delete_file, list_files, FileNotFoundError,
                        get_files_by_name, get_ngroup_id_for_file,
                        AuthorizationError)
from v1.utils.collection import get_collection as get_collection_util, CollectionNotFoundError

from lambda_utils.type_util.file import FileCreate, FileReturn, FileUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file", tags=["file"])

# Note: Removed the separate get_user_ngroup_id helper function from here

# --- Endpoints ---

@router.post("/", response_model=FileReturn)
async def create_file_endpoint(
    file: FileCreate,
    # Use the new dependency that includes ngroup_id lookup
    current_user: dict = Depends(get_current_user_with_ngroup)
):
    """
    Creates a file metadata record. Auth required. Verifies collection belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id'] # Get ngroup_id from the enhanced dependency result

    try:
        # Pass user_ngroup_id to util function for validation
        return await create_file(file, user_ngroup_id)
    except AuthorizationError as e:
         raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(f"Failed in create_file_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in create_file_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error creating file record.")


@router.get("/find", response_model=List[FileReturn])
async def lookup_file_endpoint(
    name: str = Query(..., description="File name to search for"),
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID"),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Finds file records by name within a specific NGROUP. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized to search in the specified ngroup.")

    try:
        files = await get_files_by_name(name, ngroup_id)
        return files
    except ValueError as e:
        logger.error(f"Value error during file lookup by name '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during file lookup by name '{name}' for ngroup {ngroup_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during file lookup.")


@router.get("/{file_id}", response_model=FileReturn)
async def get_file_endpoint(
    file_id: UUID,
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Retrieves a specific file record by ID. Auth required. Verifies file belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id']
    try:
        resource_ngroup_id = await get_ngroup_id_for_file(file_id)
        if resource_ngroup_id is None:
             raise FileNotFoundError(file_id=file_id)
        if resource_ngroup_id != user_ngroup_id:
             raise HTTPException(status_code=403, detail="Not authorized to access this file.")

        file_record = await get_file(file_id) # Changed variable name for clarity
        return file_record
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error getting file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error getting file.")


@router.patch("/{file_id}", response_model=FileReturn)
async def update_file_endpoint(
    file_id: UUID,
    file_update: FileUpdate,
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Updates a file metadata record. Auth required. Verifies file belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id']
    try:
        resource_ngroup_id = await get_ngroup_id_for_file(file_id)
        if resource_ngroup_id is None:
             raise FileNotFoundError(file_id=file_id)
        if resource_ngroup_id != user_ngroup_id:
             raise HTTPException(status_code=403, detail="Not authorized to update this file.")

        # Check if attempting to change collection_id and validate target collection
        if file_update.collection_id is not None:
             try:
                  # Ensure new collection is in the user's group using the collection util
                  await get_collection_util(file_update.collection_id, user_ngroup_id)
             except CollectionNotFoundError:
                  raise HTTPException(status_code=400, detail=f"Target collection {file_update.collection_id} invalid or not accessible.")

        updated_file = await update_file(file_id, file_update)
        return updated_file
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Failed updating file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error updating file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error updating file.")

@router.delete("/{file_id}", response_model=bool)
async def delete_file_endpoint(
    file_id: UUID,
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Deletes a file metadata record. Auth required. Verifies file belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id']
    try:
        resource_ngroup_id = await get_ngroup_id_for_file(file_id)
        if resource_ngroup_id is None:
             raise FileNotFoundError(file_id=file_id)
        if resource_ngroup_id != user_ngroup_id:
             raise HTTPException(status_code=403, detail="Not authorized to delete this file.")

        success = await delete_file(file_id)
        return success
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error deleting file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error deleting file.")

@router.get("/", response_model=List[FileReturn])
async def list_files_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID"),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Lists file records for a specific NGROUP. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized to list files for the specified ngroup.")

    try:
        return await list_files(ngroup_id)
    except ValueError as e:
        logger.error(f"Value error listing files for ngroup {ngroup_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing files for ngroup {ngroup_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error listing files.")