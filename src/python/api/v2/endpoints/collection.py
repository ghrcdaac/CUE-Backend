# File: src/python/api/v2/endpoints/collection.py

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import collection as collection_utils
from v2.type_util.collection import CollectionCreate, CollectionUpdate, CollectionResponse

router = APIRouter(prefix="/collections", tags=["V2 - Collections"])

@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("collection:create"))])
async def create_collection_endpoint(collection: CollectionCreate, user: AuthUser = Depends(get_current_user)):
    """Creates a new collection within the user's active ngroup."""
    if "admin" not in user.roles and not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    
    ngroup_id = UUID(user.active_ngroup_id)
    try:
        new_collection = await collection_utils.create_collection(collection, ngroup_id)
        return CollectionResponse.model_validate(new_collection)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[CollectionResponse], dependencies=[Depends(require_privilege("collection:read"))])
async def list_collections_endpoint(user: AuthUser = Depends(get_current_user)):
    """Retrieves all collections for the user's active ngroup."""
    if "admin" not in user.roles and not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")

    ngroup_id = UUID(user.active_ngroup_id)
    try:
        return await collection_utils.list_collections(ngroup_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{collection_id}", response_model=CollectionResponse, dependencies=[Depends(require_privilege("collection:read"))])
async def get_collection_endpoint(collection_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Retrieves a single collection by its ID."""
    try:
        collection = await collection_utils.get_collection(collection_id)
        if "admin" not in user.roles and str(collection['ngroup_id']) not in user.ngroups:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return CollectionResponse.model_validate(collection)
    except collection_utils.CollectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{collection_id}", response_model=CollectionResponse, dependencies=[Depends(require_privilege("collection:update"))])
async def update_collection_endpoint(collection_id: UUID, collection_update: CollectionUpdate, user: AuthUser = Depends(get_current_user)):
    """Updates an existing collection."""
    try:
        collection_to_update = await collection_utils.get_collection(collection_id)
        if "admin" not in user.roles and str(collection_to_update['ngroup_id']) not in user.ngroups:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        
        updated_collection = await collection_utils.update_collection(collection_id, collection_update)
        return CollectionResponse.model_validate(updated_collection)
    except collection_utils.CollectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("collection:delete"))])
async def delete_collection_endpoint(collection_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Deletes a collection."""
    try:
        collection_to_delete = await collection_utils.get_collection(collection_id)
        if "admin" not in user.roles and str(collection_to_delete['ngroup_id']) not in user.ngroups:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        await collection_utils.delete_collection(collection_id)
    except collection_utils.CollectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e: # Catches FK violation from the util layer
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))