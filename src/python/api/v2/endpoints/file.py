# File: src/python/api/v2/endpoints/file.py (Updated)

from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import file as file_utils
from v2.type_util.file import FileResponse, PaginatedFileResponse, FileUpdateRequest
from v2.database_util import collection as collection_db
router = APIRouter(prefix="/files", tags=["V2 - Files"])

@router.get("/", response_model=PaginatedFileResponse)
async def list_files_endpoint(
    user: AuthUser = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number."),
    page_size: int = Query(50, ge=1, le=100, description="Items per page."),
    _privilege: None = Depends(require_privilege("file:read"))
):
    """Lists files for the user's active ngroup with pagination."""
    if "admin" not in user.roles and not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")

    ngroup_id_to_query = UUID(user.active_ngroup_id)
    try:
        items, total = await file_utils.list_files(ngroup_id_to_query, page, page_size)
        return PaginatedFileResponse(items=items, total=total, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{file_id}", response_model=FileResponse)
async def get_file_endpoint(
    file_id: UUID, user: AuthUser = Depends(get_current_user),
    _privilege: None = Depends(require_privilege("file:read"))
):
    """Retrieves detailed information for a single file."""
    try:
        file_details = await file_utils.get_file_details(file_id)
        if "admin" not in user.roles:
            file_ngroup_id = (await collection_db.get_collection_by_id(file_details['collection_id']))['ngroup_id']
            if str(file_ngroup_id) not in user.ngroups:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this file.")
        
        return FileResponse.model_validate(file_details)
    except file_utils.FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{file_id}", response_model=FileResponse)
async def update_file_endpoint(
    file_id: UUID,
    file_update: FileUpdateRequest,
    user: AuthUser = Depends(get_current_user),
    _privilege: None = Depends(require_privilege("file:update"))
):
    """Updates a file's descriptive metadata (e.g., name, collection_path)."""
    try:
        file_details = await file_utils.get_file_details(file_id)
        if "admin" not in user.roles:
            file_ngroup_id = (await collection_db.get_collection_by_id(file_details['collection_id']))['ngroup_id']
            if str(file_ngroup_id) not in user.ngroups:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to update this file.")
        
        updated_file = await file_utils.update_file(file_id, file_update)
        return FileResponse.model_validate(updated_file)
    except file_utils.FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_endpoint(
    file_id: UUID, user: AuthUser = Depends(get_current_user),
    _privilege: None = Depends(require_privilege("file:delete"))
):
    """Deletes a file and its associated records."""
    try:
        file_details = await file_utils.get_file_details(file_id)
        if "admin" not in user.roles:
            file_ngroup_id = (await collection_db.get_collection_by_id(file_details['collection_id']))['ngroup_id']
            if str(file_ngroup_id) not in user.ngroups:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to delete this file.")

        await file_utils.delete_file(file_id)
    except file_utils.FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))