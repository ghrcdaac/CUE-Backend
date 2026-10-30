# ==============================================================================
# File: src/python/api/v2/database_util/collection_provider.py
# Purpose: SQL for collection <-> provider many-to-many mappings.
#          collection.provider_id stays the "primary"; reads go through v_collection_provider.
# ==============================================================================
from typing import Any, Dict, List, Set
from uuid import UUID

from asyncpg import Connection


async def list_providers_for_collection(conn: Connection, collection_id: UUID) -> List[Dict[str, Any]]:
    query = """
        SELECT p.id AS provider_id, p.short_name, p.long_name, p.can_upload, p.ngroup_id,
               (p.id = c.provider_id) AS is_primary
        FROM v_collection_provider vcp
        JOIN collection c ON c.id = vcp.collection_id
        JOIN provider p ON p.id = vcp.provider_id
        WHERE vcp.collection_id = $1
        ORDER BY (p.id = c.provider_id) DESC, p.short_name;
    """
    return await conn.fetch(query, collection_id)


async def mapped_provider_ids(conn: Connection, collection_id: UUID) -> Set[UUID]:
    rows = await conn.fetch("SELECT provider_id FROM v_collection_provider WHERE collection_id = $1", collection_id)
    return {r["provider_id"] for r in rows}


async def add_mapping(conn: Connection, collection_id: UUID, provider_id: UUID, actor_id) -> bool:
    """Inserts a mapping row. Returns False if the row already existed."""
    result = await conn.fetchval(
        """INSERT INTO collection_provider (collection_id, provider_id, created_by)
           VALUES ($1, $2, $3) ON CONFLICT DO NOTHING RETURNING provider_id""",
        collection_id, provider_id, actor_id,
    )
    return result is not None


async def remove_mapping(conn: Connection, collection_id: UUID, provider_id: UUID) -> bool:
    result = await conn.execute(
        "DELETE FROM collection_provider WHERE collection_id = $1 AND provider_id = $2", collection_id, provider_id
    )
    return result.strip() == "DELETE 1"


async def set_primary(conn: Connection, collection_id: UUID, provider_id: UUID) -> None:
    await conn.execute("UPDATE collection SET provider_id = $1 WHERE id = $2", provider_id, collection_id)


async def list_collections_for_provider(conn: Connection, provider_id: UUID) -> List[Dict[str, Any]]:
    query = """
        SELECT c.id AS collection_id, c.short_name, c.active, c.ngroup_id,
               (c.provider_id = $1) AS is_primary
        FROM v_collection_provider vcp
        JOIN collection c ON c.id = vcp.collection_id AND c.is_deleted = FALSE
        WHERE vcp.provider_id = $1
        ORDER BY c.short_name;
    """
    return await conn.fetch(query, provider_id)


async def upload_providers_for_collection(conn: Connection, collection_id: UUID, user_id) -> List[Dict[str, Any]]:
    """Mapped providers of a collection with can_upload and whether the user is assigned (strict upload rule)."""
    query = """
        SELECT p.id AS provider_id, p.can_upload,
               EXISTS (SELECT 1 FROM cueuser_provider up
                       WHERE up.cueuser_id = $2 AND up.provider_id = p.id) AS assigned
        FROM v_collection_provider vcp
        JOIN provider p ON p.id = vcp.provider_id
        WHERE vcp.collection_id = $1;
    """
    return await conn.fetch(query, collection_id, user_id)


async def providers_for_collections(conn: Connection, collection_ids: List[UUID]) -> Dict[UUID, List[Dict[str, Any]]]:
    """Mapped providers for many collections at once (for list responses)."""
    if not collection_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT vcp.collection_id, p.id AS provider_id, p.short_name, p.long_name, p.can_upload,
               (p.id = c.provider_id) AS is_primary
        FROM v_collection_provider vcp
        JOIN collection c ON c.id = vcp.collection_id
        JOIN provider p ON p.id = vcp.provider_id
        WHERE vcp.collection_id = ANY($1::uuid[])
        ORDER BY vcp.collection_id, (p.id = c.provider_id) DESC, p.short_name;
        """,
        collection_ids,
    )
    out: Dict[UUID, List[Dict[str, Any]]] = {}
    for r in rows:
        out.setdefault(r["collection_id"], []).append(dict(r))
    return out
