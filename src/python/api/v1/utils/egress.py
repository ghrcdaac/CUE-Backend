from uuid import UUID
from typing import List, Optional
from asyncpg.pool import Pool

from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import egress as egress_db
from v1.utils.ngroup import get_ngroup, NgroupNotFoundError 
from lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate

# Custom exception for consistent error handling
class EgressNotFoundError(Exception):
    def __init__(self, egress_id: UUID = None, ngroup_id: UUID = None):
        if egress_id and ngroup_id:
            message = f"Egress not found with ID: {egress_id} and ngroup_id: {ngroup_id}"
        elif egress_id:
            message = f"Egress not found with ID: {egress_id}"
        else:
            message = "Egress not found"
        super().__init__(message)
        self.egress_id = egress_id
        self.ngroup_id = ngroup_id

async def create_egress(egress: EgressCreate) -> EgressReturn:
    """Creates a new egress record."""
    try:
        # Validate ngroup existence (still needed for creation)
        await get_ngroup(egress.ngroup_id)  # Raises NgroupNotFoundError if not found
    except NgroupNotFoundError:
        raise ValueError(f"Ngroup with ID '{egress.ngroup_id}' not found")

    pool: Pool = await get_connection_pool()
    params = (egress.type, egress.path, egress.config, egress.ngroup_id)
    try:
        result = await query(pool, egress_db.create_egress_in_db, params, row_mapper=EgressReturn.from_db_row)
        return result[0]
    except Exception as e:
        raise ValueError(f"Failed to create egress: {e}")
    finally:
        await pool.close()

async def get_egress(egress_id: UUID, ngroup_id: UUID) -> EgressReturn | None:
    """Retrieves an egress record by its ID, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (egress_id, ngroup_id)  # Include ngroup_id
    try:
        result = await query(pool, egress_db.get_egress_from_db, params, row_mapper=EgressReturn.from_db_row)
        return result[0] if result else None  # Return None if not found
    except Exception as e:
        raise ValueError(f"Failed to get egress: {e}")
    finally:
        await pool.close()

async def update_egress(egress_id: UUID, egress_update: EgressUpdate) -> EgressReturn | None:
    """Updates an existing egress record."""
    pool: Pool = await get_connection_pool()
    update_fields = {
        k: v for k, v in egress_update.model_dump().items() if v is not None
    }
    if not update_fields:  # No update fields provided
        return await get_egress(egress_id) #No need to check for ngroup for just checking the update

    params = (update_fields, egress_id)
    try:
        result = await query(pool, egress_db.update_egress_in_db, params, row_mapper=EgressReturn.from_db_row)
        return result[0] if result else None # Return None if not found
    except Exception as e:
        raise ValueError(f"Failed to update egress: {e}")
    finally:
        await pool.close()

async def list_egresses(ngroup_id: UUID) -> List[EgressReturn]:
    """Retrieves all egress records, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id,)  # Pass ngroup_id as a tuple
    try:
        results = await query(pool, egress_db.list_egresses_from_db, params, row_mapper=EgressReturn.from_db_row)
        return results
    except Exception as e:
        raise ValueError(f"Failed to list egresses: {e}")
    finally:
        await pool.close()

async def delete_egress(egress_id: UUID, ngroup_id: UUID) -> bool:
    """Deletes an egress record by its ID, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (egress_id, ngroup_id)  # Include ngroup_id
    try:
        result = await query(pool, egress_db.delete_egress_from_db, params)
        return result  # Return True if deleted, False otherwise
    except Exception as e:
        print(f"Error deleting egress: {e}")
        return False  # Consistent return type
    finally:
        await pool.close()