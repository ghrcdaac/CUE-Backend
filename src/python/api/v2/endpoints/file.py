# ==============================================================================
# File: src/python/api/v2/endpoints/file.py (Complete & Corrected)
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import file as file_utils
from v2.type_util.file import FileResponse, PaginatedFileResponse, FileUpdateRequest
from v2.utils.authorization import check_user_access_to_file # Centralized auth helper

router = APIRouter(prefix="/files", tags=["V2 - Files"])


@router.get("/", response_model=PaginatedFileResponse, dependencies=[Depends(require_privilege("file:read"))])
async def list_files_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter files by status (e.g., 'infected', 'clean')."),
    page: int = Query(1, ge=1, description="Page number."),
    page_size: int = Query(50, ge=1, le=100, description="Items per page.")
):
    """
    Lists files for the user's active ngroup with pagination.
    Optionally filters the list by file status.
    """
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")

    ngroup_id_to_query = UUID(user.active_ngroup_id)
    try:
        # --- FEATURE ADDED: Pass the optional status filter down to the util layer ---
        items, total = await file_utils.list_files(request, ngroup_id_to_query, page, page_size, status)
        return PaginatedFileResponse(items=items, total=total, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- FEATURE ADDED: Restored the 'find by name' endpoint from V1 ---
@router.get("/find", response_model=List[FileResponse], dependencies=[Depends(require_privilege("file:read"))])
async def find_files_by_name_endpoint(
    request: Request,
    name: str = Query(..., description="File name to search for."),
    user: AuthUser = Depends(get_current_user)
):
    """Finds file records by name within the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")

    ngroup_id = UUID(user.active_ngroup_id)
    try:
        return await file_utils.find_files_by_name(request, ngroup_id, name)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error finding files: {e}")

@router.get("/{file_id}", response_model=FileResponse, dependencies=[Depends(require_privilege("file:read"))])
async def get_file_endpoint(
    request: Request,
    file_id: UUID, 
    user: AuthUser = Depends(get_current_user)
):
    """Retrieves detailed information for a single file."""
    try:
        # ---   Use a robust, centralized permission check ---
        await check_user_access_to_file(request, user, file_id)
        
        file_details = await file_utils.get_file_details(request, file_id)
        return FileResponse.model_validate(file_details)
    except file_utils.FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException as e:
        raise e # Re-raise auth-related HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{file_id}", response_model=FileResponse, dependencies=[Depends(require_privilege("file:update"))])
async def update_file_endpoint(
    request: Request,
    file_id: UUID,
    file_update: FileUpdateRequest,
    user: AuthUser = Depends(get_current_user)
):
    """Updates a file's descriptive metadata (e.g., name, collection_path)."""
    try:
        # ---   Use a robust, centralized permission check ---
        await check_user_access_to_file(request, user, file_id)
        
        updated_file = await file_utils.update_file(request, file_id, file_update)
        return FileResponse.model_validate(updated_file)
    except file_utils.FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("file:delete"))])
async def delete_file_endpoint(
    request: Request,
    file_id: UUID, 
    user: AuthUser = Depends(get_current_user)
):
    """Deletes a file and its associated records."""
    try:
        # ---   Use a robust, centralized permission check ---
        await check_user_access_to_file(request, user, file_id)

        await file_utils.delete_file(request, file_id)
    except file_utils.FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))