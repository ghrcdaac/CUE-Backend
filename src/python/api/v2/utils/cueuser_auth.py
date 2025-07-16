from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import cueuser_auth as cueuser_auth_db
from lambda_utils.type_util.cueuser_auth import CueuserAuthCreate, CueuserAuthReturn, CueuserAuthUpdate
from typing import List
from uuid import UUID
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CueuserAuthNotFoundError(Exception):
    def __init__(self, cueuser_auth_id: UUID):
        super().__init__(f"Cueuser authentication record not found with ID: {cueuser_auth_id}")
        self.cueuser_auth_id = cueuser_auth_id

async def create_cueuser_auth(cueuser_auth: CueuserAuthCreate) -> bool:
    """Creates a new cueuser_auth record."""
    pool: Pool = await get_connection_pool()
    # Set the last_login timestamp to the current UTC time on the server-side
    last_login_dt = datetime.now(timezone.utc)
    params = (cueuser_auth.id, cueuser_auth.refresh_token, last_login_dt)
    try:
        result = await query(pool, cueuser_auth_db.create_cueuser_auth_in_db, params)
        return result
    except Exception as e:
        logger.error(f"Error creating cueuser_auth: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_cueuser_auth(cueuser_auth_id: UUID) -> CueuserAuthReturn | None:
    """Retrieves a cueuser_auth record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_auth_id,)
    try:
        result = await query(pool, cueuser_auth_db.get_cueuser_auth_from_db, params, row_mapper=CueuserAuthReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserAuthNotFoundError(cueuser_auth_id=cueuser_auth_id)
    except Exception as e:
        logger.error(f"Error getting cueuser_auth: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_cueuser_auth(cueuser_auth_id: UUID, cueuser_auth_update: CueuserAuthUpdate) -> CueuserAuthReturn | None:
    """Updates an existing cueuser_auth record."""
    pool: Pool = await get_connection_pool()
    update_fields = {
        "refresh_token": cueuser_auth_update.refresh_token
    }

    # Update last_login only if it's provided
    if cueuser_auth_update.last_login is not None:
        update_fields["last_login"] = cueuser_auth_update.last_login

    params = (update_fields, cueuser_auth_id)
    try:
        result = await query(pool, cueuser_auth_db.update_cueuser_auth_in_db, params, row_mapper=CueuserAuthReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserAuthNotFoundError(cueuser_auth_id=cueuser_auth_id)
    except Exception as e:
        logger.error(f"Error updating cueuser_auth: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_cueuser_auth(cueuser_auth_id: UUID) -> bool:
    """Deletes a cueuser_auth record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_auth_id,)
    try:
        result = await query(pool, cueuser_auth_db.delete_cueuser_auth_from_db, params)
        if not result:
            raise CueuserAuthNotFoundError(cueuser_auth_id=cueuser_auth_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting cueuser_auth: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_cueuser_auths() -> List[CueuserAuthReturn]:
    """Retrieves all cueuser_auth records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, cueuser_auth_db.list_cueuser_auths_from_db, row_mapper=CueuserAuthReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing cueuser_auths: {e}", exc_info=True)
        raise
    finally:
        await pool.close()