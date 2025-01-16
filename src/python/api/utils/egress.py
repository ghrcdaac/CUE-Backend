from uuid import UUID
from typing import List, Dict, Any
from asyncpg.pool import Pool

from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import egress as egress_db
from lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate

async def create_egress(egress: EgressCreate) -> EgressReturn:
    """Creates a new egress record."""
    pool: Pool = await get_connection_pool()
    params = (egress.type, egress.path, egress.config, egress.ngroup_id)
    result = await query(pool, egress_db.create_egress_in_db, params, row_mapper=EgressReturn.from_db_row)
    await pool.close()
    return result[0]

async def get_egress(egress_id: UUID) -> EgressReturn | None:
    """Retrieves an egress record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (egress_id,)
    result = await query(pool, egress_db.get_egress_from_db, params, row_mapper=EgressReturn.from_db_row)
    await pool.close()
    return result[0] if result else None

async def update_egress(egress_id: UUID, egress_update: EgressUpdate) -> EgressReturn | None:
    """Updates an existing egress record."""
    pool: Pool = await get_connection_pool()
    update_fields = {
        k: v for k, v in egress_update.model_dump().items() if v is not None
    }
    if not update_fields:
        return await get_egress(egress_id)  # No fields to update

    params = (update_fields, egress_id)
    result = await query(pool, egress_db.update_egress_in_db, params, row_mapper=EgressReturn.from_db_row)
    await pool.close()
    return result[0] if result else None

async def list_egresses() -> List[EgressReturn]:
    """Retrieves all egress records."""
    pool: Pool = await get_connection_pool()
    results = await query(pool, egress_db.list_egresses_from_db, row_mapper=EgressReturn.from_db_row)
    await pool.close()
    return results