from asyncpg import Connection, ForeignKeyViolationError, UniqueViolationError, DataError
from typing import Tuple, List, Optional, Dict, Any
from lambda_utils.type_util.egress import EgressReturn
from uuid import UUID
import json
import logging

logger = logging.getLogger(__name__)

async def create_egress_in_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Inserts a new egress record into the database."""
    insert_query = """
        INSERT INTO egress (type, path, config, ngroup_id)
        VALUES ($1, $2, $3::jsonb, $4)
        RETURNING id, type, path, config, ngroup_id
    """
    try:
        config_json = json.dumps(params[2])  # Ensure config is JSON string
        return await conn.fetch(insert_query, params[0], params[1], config_json, params[3])
    except ForeignKeyViolationError:
        logger.error(f"Failed to create egress: Foreign key violation (ngroup_id)", exc_info=True)
        raise ValueError(f"Ngroup with ID '{params[3]}' not found")
    except UniqueViolationError as e:
        logger.error(f"Failed to create egress: Unique constraint violation: {e}", exc_info=True)
        raise ValueError("Unique constraint violation.")
    except DataError as e:
        logger.error(f"Failed to create egress: Data error: {e}", exc_info=True)
        raise ValueError("Invalid data.")
    except Exception as e:
        logger.error(f"Failed to create egress: {e}", exc_info=True)
        raise

async def get_egress_from_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Retrieves an egress record by its ID, filtered by ngroup_id."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
        WHERE id = $1 AND ngroup_id = $2  -- Filter by ID and ngroup_id
    """
    try:
        return await conn.fetch(select_query, *params)  # Use *params
    except Exception as e:
        logger.error(f"Error getting egress: {e}", exc_info=True)
        raise

async def update_egress_in_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Updates an existing egress record in the database."""
    update_fields: Dict = params[0]
    egress_id: UUID = params[1]

    set_clause_parts = []
    values = []
    for i, (field, value) in enumerate(update_fields.items()):
        if field == "config":
            values.append(json.dumps(value)) # Convert config to JSON
        else:
            values.append(value)
        set_clause_parts.append(f"{field} = ${len(values)}")

    values.append(egress_id)
    set_clause = ", ".join(set_clause_parts)

    update_query = f"""
        UPDATE egress
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, type, path, config, ngroup_id
    """
    try:
        return await conn.fetch(update_query, *values)  # Use *values for parameters
    except ForeignKeyViolationError:
        logger.error(f"Failed to update egress: Foreign key violation (ngroup_id)", exc_info=True)
        raise ValueError(f"Ngroup ID not found")
    except UniqueViolationError as e:
        logger.error(f"Failed to update egress: Unique constraint violation: {e}", exc_info=True)
        raise ValueError("Unique constraint violation.")
    except DataError as e:
        logger.error(f"Failed to update egress: Data error: {e}", exc_info=True)
        raise ValueError("Invalid data.")
    except Exception as e:
        logger.error(f"Failed to update egress: {e}", exc_info=True)
        raise

async def list_egresses_from_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Retrieves all egress records, filtered by ngroup_id."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
        WHERE ngroup_id = $1  -- Filter by ngroup_id
    """
    try:
        return await conn.fetch(select_query, *params) # Use *params
    except Exception as e:
        logger.error(f"Error listing egresses: {e}", exc_info=True)
        raise

async def delete_egress_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes an egress record by its ID, filtered by ngroup_id."""
    delete_query = """
        DELETE FROM egress
        WHERE id = $1 AND ngroup_id = $2  -- Filter by ID and ngroup_id
    """
    try:
        result = await conn.execute(delete_query, *params)  # Use *params
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"Error deleting egress: {e}", exc_info=True)
        raise