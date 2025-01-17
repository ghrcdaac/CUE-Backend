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
        config_json = json.dumps(params[2])
        return await conn.fetch(insert_query, params[0], params[1], config_json, params[3])
    except ForeignKeyViolationError:
        logger.error(f"Failed to create egress due to foreign key violation: ngroup_id {params[3]} not found", exc_info=True)
        raise ValueError(f"Ngroup with ID '{params[3]}' not found")
    except UniqueViolationError as e:
        logger.error(f"Failed to create egress due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("An egress record with similar attributes already exists.")
    except DataError as e:
        logger.error(f"Failed to create egress due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating an egress record.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating an egress record: {e}", exc_info=True)
        raise

async def get_egress_from_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Retrieves an egress record from the database by its ID."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting an egress record: {e}", exc_info=True)
        raise

async def update_egress_in_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Updates an existing egress record in the database."""
    update_fields: Dict = params[0]
    egress_id: UUID = params[1]

    set_clause_parts = []
    values = []
    for i, (field, value) in enumerate(update_fields.items()):
        if field == "config":
            values.append(json.dumps(value))
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
        return await conn.fetch(update_query, *values)
    except ForeignKeyViolationError:
        logger.error(f"Failed to update egress due to foreign key violation: ngroup_id {params[0].get('ngroup_id')} not found", exc_info=True)
        raise ValueError(f"Ngroup with ID '{params[0].get('ngroup_id')}' not found")
    except UniqueViolationError as e:
        logger.error(f"Failed to update egress due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("An egress record with similar attributes already exists.")
    except DataError as e:
        logger.error(f"Failed to update egress due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating an egress record.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating an egress record: {e}", exc_info=True)
        raise

async def list_egresses_from_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Retrieves all egress records from the database."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing egress records: {e}", exc_info=True)
        raise

async def delete_egress_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes an egress record from the database by its ID."""
    delete_query = """
        DELETE FROM egress
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting an egress record: {e}", exc_info=True)
        raise