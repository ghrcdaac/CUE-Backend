# ==============================================================================
# File: src/python/api/v2/endpoints/collection.py (Corrected)
# --- MODIFIED to robustly handle the structure of user.ngroups ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import collection as collection_utils
from v2.type_util.collection import CollectionCreate, CollectionUpdate, CollectionResponse,PaginatedCollectionResponse

router = APIRouter(prefix="/collections", tags=["V2 - Collections"])

@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("collection:create"))])
async def create_collection_endpoint(
    request: Request, 
    collection: CollectionCreate, 
    user: AuthUser = Depends(get_current_user)
):
    """Creates a new collection within the user's active ngroup."""
    if "admin" not in user.roles and not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    
    ngroup_id = UUID(user.active_ngroup_id)
    try:
        new_collection = await collection_utils.create_collection(request, collection, ngroup_id)
        return CollectionResponse.model_validate(new_collection)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=PaginatedCollectionResponse, dependencies=[Depends(require_privilege("collection:read"))])
async def list_collections_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    #  Read the active ngroup ID directly from the header
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50)
):
    """Retrieves all collections, filtered by the user's active ngroup from the header."""
    if "admin" not in user.roles and not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    
    try:
        # Pass the header value and the user object to the utility function
        return await collection_utils.list_collections(request, user, active_ngroup_id, page, page_size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{collection_id}", response_model=CollectionResponse, dependencies=[Depends(require_privilege("collection:read"))])
async def get_collection_endpoint(request: Request, collection_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Retrieves a single collection by its ID."""
    try:
        collection = await collection_utils.get_collection(request, collection_id)
        is_admin = "admin" in user.roles
        
        # --- Robustly build the user_ngroup_ids set ---
        user_ngroup_ids = set()
        if user.ngroups:
            if isinstance(user.ngroups[0], dict):
                user_ngroup_ids = {str(ng['id']) for ng in user.ngroups}
            else:
                user_ngroup_ids = {str(ng) for ng in user.ngroups}

        if not is_admin and str(collection['ngroup_id']) not in user_ngroup_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return CollectionResponse.model_validate(collection)
    except collection_utils.CollectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/{collection_id}", response_model=CollectionResponse, dependencies=[Depends(require_privilege("collection:update"))])
async def update_collection_endpoint(
    request: Request, 
    collection_id: UUID, 
    collection_update: CollectionUpdate, 
    user: AuthUser = Depends(get_current_user)
):
    """Updates an existing collection."""
    try:
        # First, get the collection we intend to update
        collection_to_update = await collection_utils.get_collection(request, collection_id)
        
        is_admin = "admin" in user.roles
        # A non-admin user can only update a collection within their currently active ngroup
        if not is_admin and str(collection_to_update['ngroup_id']) != user.active_ngroup_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Collection is not in your active DAAC group.")
        
        # Pass the already-fetched collection to the update function to avoid a second DB call
        updated_collection = await collection_utils.update_collection(
            request, collection_id, collection_update, collection_to_update
        )
        return CollectionResponse.model_validate(updated_collection)
        
    except collection_utils.CollectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e:
        raise e # Re-raise auth exceptions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("collection:delete"))])
async def delete_collection_endpoint(request: Request, collection_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Deletes a collection."""
    try:
        collection_to_delete = await collection_utils.get_collection(request, collection_id)
        is_admin = "admin" in user.roles

        # --- Robustly build the user_ngroup_ids set ---
        user_ngroup_ids = set()
        if user.ngroups:
            if isinstance(user.ngroups[0], dict):
                user_ngroup_ids = {str(ng['id']) for ng in user.ngroups}
            else:
                user_ngroup_ids = {str(ng) for ng in user.ngroups}
        
        if not is_admin and str(collection_to_delete['ngroup_id']) not in user_ngroup_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        await collection_utils.delete_collection(request, collection_id)
    except collection_utils.CollectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e: 
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))