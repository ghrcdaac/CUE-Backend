import uuid
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import user_application as user_application_db
from lambda_utils.type_util.user_application import UserApplicationCreate, UserApplicationReturn, UserApplicationUpdate
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timezone

from v1.utils.ngroup import list_ngroups
from v1.utils.provider import list_providers
from lambda_utils.type_util.ngroup import NgroupListReturn
from lambda_utils.type_util.provider import ProviderListReturn


logger = logging.getLogger(__name__)

class UserApplicationNotFoundError(Exception):
    def __init__(self, user_application_id: UUID, ngroup_id: Optional[UUID] = None):
        message = f"User application not found with ID: {user_application_id}"
        if ngroup_id:
            message += f" and ngroup_id: {ngroup_id}"
        super().__init__(message)
        self.user_application_id = user_application_id
        self.ngroup_id = ngroup_id
class UnauthorizedError(Exception): #custom error if the user is not authorized
    pass

async def create_user_application(user_application: UserApplicationCreate) -> UserApplicationReturn:
    """Creates a new user_application record."""
    pool: Pool = await get_connection_pool()
    # Set the applied timestamp to the current UTC time on the server-side
    applied_dt = datetime.now(timezone.utc)

    params = (user_application.email, user_application.name, applied_dt, user_application.username, "pending", user_application.ngroup_id, user_application.provider_id, user_application.justification, user_application.account_type, user_application.edpub_id)
    try:
        result = await query(pool, user_application_db.create_user_application_in_db, params, row_mapper=UserApplicationReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating user_application: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_user_application(user_application_id: UUID, ngroup_id: Optional[UUID] = None) -> UserApplicationReturn | None:
    """Retrieves a user_application record by its ID, optionally filtering by ngroup ID."""
    pool: Pool = await get_connection_pool()
    try:
        
        params = (user_application_id, ngroup_id)
        result = await query(pool, user_application_db.get_user_application_from_db, params, row_mapper=UserApplicationReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise UserApplicationNotFoundError(user_application_id=user_application_id, ngroup_id=ngroup_id)
    except Exception as e:
        logger.error(f"Error getting user_application: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_user_application(user_application_id: UUID, user_application_update: UserApplicationUpdate) -> UserApplicationReturn | None:
    """Updates an existing user_application record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in user_application_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_user_application(user_application_id) 

    params = (update_fields, user_application_id)  
    try:
        result = await query(pool, user_application_db.update_user_application_in_db, params, row_mapper=UserApplicationReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise UserApplicationNotFoundError(user_application_id=user_application_id)
    except Exception as e:
        logger.error(f"Error updating user_application: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_user_application(user_application_id: UUID, ngroup_id: Optional[UUID] = None) -> bool:
    """Deletes a user_application record by its ID, optionally filtering by ngroup ID."""
    pool: Pool = await get_connection_pool()
    try:
        params = (user_application_id, ngroup_id)
        result = await query(pool, user_application_db.delete_user_application_from_db, params)
        if not result:
             raise UserApplicationNotFoundError(user_application_id=user_application_id, ngroup_id=ngroup_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting user_application: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_user_applications(ngroup_id: Optional[UUID] = None) -> List[UserApplicationReturn]:
    """Retrieves all user_application records, optionally filtering by ngroup ID."""
    pool: Pool = await get_connection_pool()
    try:
        params = (ngroup_id,) if ngroup_id else None  
        results = await query(pool, user_application_db.list_user_applications_from_db, params, row_mapper=UserApplicationReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing user_applications: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_ngroups_for_form() -> List[NgroupListReturn]:
    """Retrieves a list of ngroups with id and short_name for form."""
    return await list_ngroups()  # Reuse the existing ngroup listing function

async def get_providers_for_ngroup(ngroup_id: UUID) -> List[ProviderListReturn]:
    """Retrieves a list of providers for a specific ngroup."""
    return await list_providers(ngroup_id=ngroup_id)