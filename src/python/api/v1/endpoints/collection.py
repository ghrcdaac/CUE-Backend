from fastapi import APIRouter, HTTPException, Query, Path, Depends
from uuid import UUID
from typing import List, Optional

from v1.utils.collection import (create_collection, get_collection,
                              list_files_for_collection, update_collection,
                              delete_collection, list_collections,
                              CollectionNotFoundError, get_collection_by_lookup)
from lambda_utils.type_util.collection import (CollectionCreate, CollectionReturn,
                                              CollectionUpdate, PaginatedFiles)
from lambda_utils.type_util.file import FileReturn

# Authentication Imports
from v1.utils.auth import get_cognito_auth, CognitoAuth

router = APIRouter(prefix="/collection", tags=["collection"])

@router.post("/", response_model=CollectionReturn)
async def create_collection_endpoint(
    collection: CollectionCreate,
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Creates a new collection (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await create_collection(collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/find", response_model=CollectionReturn)
async def lookup_collection_endpoint(
    short_name: str = Query(..., description="Short name of the collection to search for"),
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"),  # Add ngroup_id
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Finds a collection by short_name, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        collection = await get_collection_by_lookup(short_name, ngroup_id) # Pass ngroup
        return collection
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Collection not found with short_name: {short_name} and ngroup_id: {ngroup_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{collection_id}", response_model=CollectionReturn)
async def get_collection_endpoint(
    collection_id: UUID,
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"), #Add ngroup_id
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Retrieves a collection by ID, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        collection = await get_collection(collection_id, ngroup_id) #Pass ngroup
        return collection
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{collection_id}", response_model=CollectionReturn)
async def update_collection_endpoint(
    collection_id: UUID,
    collection_update: CollectionUpdate,
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Updates a collection (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        updated_collection = await update_collection(collection_id, collection_update)
        return updated_collection
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{collection_id}", response_model=bool)
async def delete_collection_endpoint(
    collection_id: UUID,
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"),# Add ngroup_id
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Deletes a collection by ID, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        success = await delete_collection(collection_id, ngroup_id) # Pass ngroup
        return success
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=List[CollectionReturn])
async def list_collections_endpoint(
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"),  # Add ngroup_id
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Lists collections, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await list_collections(ngroup_id) # Pass ngroup
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{collection_id}/files", response_model=PaginatedFiles)
async def list_files_for_collection_endpoint(
    collection_id: UUID = Path(..., description="The ID of the collection to list files from"),
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"), # Add ngroup_id
    page: int = Query(1, description="Page number, starting from 1"),
    page_size: int = Query(10, description="Number of items per page"),
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Lists files associated with a collection, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        files, total_count = await list_files_for_collection(collection_id, ngroup_id, page, page_size) # Pass ngroup
        return {
            "files": files,
            "total_count": total_count
        }
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while listing files: {e}")


@router.patch("/{collection_id}/activate", response_model=CollectionReturn)
async def activate_collection_endpoint(
    collection_id: UUID,
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Activates a collection (requires authentication)."""
    if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await update_collection(collection_id, CollectionUpdate(active=True))
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{collection_id}/deactivate", response_model=CollectionReturn)
async def deactivate_collection_endpoint(
    collection_id: UUID,
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Add authentication
):
    """Deactivates a collection (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await update_collection(collection_id, CollectionUpdate(active=False))
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))