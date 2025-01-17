from asyncpg import Connection
from typing import Tuple, List, Optional, Dict, Any
from lambda_utils.type_util.ngroup import NgroupReturn
from uuid import UUID
import json

async def create_egress_in_db(conn: Connection, params: Tuple) -> List[Dict]:
    """Inserts a new egress record into the database."""
    insert_query = """
        INSERT INTO egress (type, path, config, ngroup_id)
        VALUES ($1, $2, $3::jsonb, $4)
        RETURNING id, type, path, config, ngroup_id
    """
    # Serialize the config dictionary to a JSON string
    config_json = json.dumps(params[2])

    # Convert ngroup_id to string if it's a UUID object
    ngroup_id_str = str(params[3]) if isinstance(params[3], UUID) else params[3]

    return await conn.fetch(insert_query, params[0], params[1], config_json, ngroup_id_str)


async def get_egress_from_db(conn: Connection, params: Tuple) -> List[Dict[str, Any]]:
    """Retrieves an egress record from the database by its ID."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
        WHERE id = $1
    """
    return await conn.fetch(select_query, *params)

async def update_egress_in_db(conn: Connection, params: Tuple) -> List[Dict[str, Any]]:
    """Updates an existing egress record in the database."""
    update_fields: Dict = params[0]
    egress_id: UUID = params[1]

    set_clause_parts = []
    values = []
    for i, (field, value) in enumerate(update_fields.items()):
        if field == "config":
            # Serialize the config dictionary to a JSON string for update
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
    return await conn.fetch(update_query, *values)

async def list_egresses_from_db(conn: Connection, params: Tuple) -> List[Dict[str, Any]]:
    """Retrieves all egress records from the database."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
    """
    return await conn.fetch(select_query)

async def delete_egress_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes an egress record from the database by its ID."""
    delete_query = """
        DELETE FROM egress
        WHERE id = $1
    """
    result = await conn.execute(delete_query, *params)
    # result is a string like 'DELETE 1' indicating the number of deleted rows
    return result == "DELETE 1"