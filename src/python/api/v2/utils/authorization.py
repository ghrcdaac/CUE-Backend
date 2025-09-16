# File: src/python/api/v2/utils/authorization.py

from uuid import UUID
from fastapi import Request, HTTPException, status
import structlog

from v2.type_util.auth import AuthUser
from v2.utils import file as file_utils
from v2.database_util import collection as collection_db

logger = structlog.get_logger(__name__)

async def check_user_access_to_file(request: Request, user: AuthUser, file_id: UUID):
    """
    Centralized function to check if a user is authorized to access a specific file.
    An admin has access to all files. A regular user must be a member of the
    ngroup that owns the file's collection.

    Raises:
        HTTPException(404): If the file or its collection is not found.
        HTTPException(403): If the user is not authorized.
    """
    if "admin" in user.roles:
        # Admins have universal access.
        return

    try:
        # Fetch the file details to get its collection ID
        file_details = await file_utils.get_file_details(request, file_id)
        collection_id = file_details.get('collection_id')
        if not collection_id:
            logger.warning("file.auth_check.no_collection", file_id=str(file_id))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File is not associated with a collection.")

        # Get the ngroup for the file's collection
        async with request.state.pool.acquire() as conn:
            collection = await collection_db.get_collection_by_id(conn, collection_id)
        
        if not collection:
            logger.warning("file.auth_check.collection_not_found", collection_id=str(collection_id))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File's associated collection not found.")

        file_ngroup_id = collection.get('ngroup_id')

        # Robustly build the user's set of ngroup IDs
        user_ngroup_ids = set()
        if user.ngroups:
            if isinstance(user.ngroups[0], dict):
                user_ngroup_ids = {str(ng['id']) for ng in user.ngroups}
            else:
                user_ngroup_ids = {str(ng) for ng in user.ngroups}
        
        # Perform the authorization check
        if str(file_ngroup_id) not in user_ngroup_ids:
            logger.warning("file.auth_check.denied", user_id=user.id, file_id=str(file_id), file_ngroup=str(file_ngroup_id))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this file.")

    except file_utils.FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found with ID: {file_id}")