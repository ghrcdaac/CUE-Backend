from uuid import UUID
from typing import List, Tuple, Optional, Dict
from asyncpg import Connection

from lambda_utils.type_util.egress import EgressReturn

async def create_egress_in_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Inserts a new egress record into the database."""
    insert_query = """
        INSERT INTO egress (type, path, config, ngroup_id)
        VALUES ($1, $2, $3, $4)
        RETURNING id, type, path, config, ngroup_id
    """
    return await conn.fetch(insert_query, *params)

async def get_egress_from_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Retrieves an egress record from the database by its ID."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
        WHERE id = $1
    """
    return await conn.fetch(select_query, *params)

async def update_egress_in_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Updates an existing egress record in the database."""
    update_fields: Dict = params[0]
    egress_id: UUID = params[1]

    set_clause_parts = []
    values = []
    for i, (field, value) in enumerate(update_fields.items()):
        if field == "config":
            set_clause_parts.append(f"{field} = ${i + 1}::jsonb")
        else:
            set_clause_parts.append(f"{field} = ${i + 1}")
        values.append(value)

    values.append(egress_id)

    set_clause = ", ".join(set_clause_parts)

    update_query = f"""
        UPDATE egress
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, type, path, config, ngroup_id
    """
    return await conn.fetch(update_query, *values)

async def list_egresses_from_db(conn: Connection, params: Tuple) -> List[EgressReturn]:
    """Retrieves all egress records from the database."""
    select_query = """
        SELECT id, type, path, config, ngroup_id
        FROM egress
    """
    return await conn.fetch(select_query)