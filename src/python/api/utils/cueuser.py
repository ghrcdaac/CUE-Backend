import uuid
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import cueuser as cueuser_db
from lambda_utils.type_util.cueuser import CueuserCreate, CueuserReturn, CueuserUpdate
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CueuserNotFoundError(Exception):
    def __init__(self, cueuser_id: UUID = None, email: str = None, cueusername: str = None, name: str = None, edpub_id: str = None):
        if cueuser_id:
            message = f"Cueuser not found with ID: {cueuser_id}"
        elif email:
            message = f"Cueuser not found with email: {email}"
        elif cueusername:
            message = f"Cueuser not found with username: {cueusername}"
        elif name:
            message = f"Cueuser not found with name: {name}"
        elif edpub_id:
            message = f"Cueuser not found with edpub_id: {edpub_id}"
        else:
            message = "Cueuser not found"
        super().__init__(message)
        self.cueuser_id = cueuser_id
        self.email = email
        self.cueusername = cueusername
        self.name = name
        self.edpub_id = edpub_id

async def create_cueuser(cueuser: CueuserCreate) -> CueuserReturn:
    """Creates a new cueuser record."""
    pool: Pool = await get_connection_pool()
    # Set the registered timestamp to the current UTC time on the server-side
    registered_dt = datetime.now(timezone.utc)
    params = (cueuser.email, cueuser.name, registered_dt, cueuser.cueusername, cueuser.edpub_id)
    try:
        result = await query(pool, cueuser_db.create_cueuser_in_db, params, row_mapper=CueuserReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_cueuser(cueuser_id: UUID) -> CueuserReturn | None:
    """Retrieves a cueuser record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id,)
    try:
        result = await query(pool, cueuser_db.get_cueuser_from_db, params, row_mapper=CueuserReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserNotFoundError(cueuser_id=cueuser_id)
    except Exception as e:
        logger.error(f"Error getting cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_cueuser(cueuser_id: UUID, cueuser_update: CueuserUpdate) -> CueuserReturn | None:
    """Updates an existing cueuser record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in cueuser_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_cueuser(cueuser_id)

    params = (update_fields, cueuser_id)
    try:
        result = await query(pool, cueuser_db.update_cueuser_in_db, params, row_mapper=CueuserReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserNotFoundError(cueuser_id=cueuser_id)
    except Exception as e:
        logger.error(f"Error updating cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_cueuser(cueuser_id: UUID) -> bool:
    """Deletes a cueuser record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id,)
    try:
        result = await query(pool, cueuser_db.delete_cueuser_from_db, params)
        if not result:
            raise CueuserNotFoundError(cueuser_id=cueuser_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_cueusers() -> List[CueuserReturn]:
    """Retrieves all cueuser records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, cueuser_db.list_cueusers_from_db, row_mapper=CueuserReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing cueusers: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_cueuser_by_lookup(
    email: Optional[str] = None,
    cueusername: Optional[str] = None,
    name: Optional[str] = None,
    edpub_id: Optional[str] = None
) -> CueuserReturn | None:
    """Retrieves a cueuser record by email, cueusername, name, or edpub_id."""
    pool: Pool = await get_connection_pool()
    params = (email, cueusername, name, edpub_id)
    try:
        result = await query(pool, cueuser_db.get_cueuser_by_lookup_from_db, params, row_mapper=CueuserReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserNotFoundError(email=email, cueusername=cueusername, name=name, edpub_id=edpub_id)
    except Exception as e:
        logger.error(f"Error during cueuser lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()