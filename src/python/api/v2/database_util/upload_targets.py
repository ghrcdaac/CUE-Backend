# ==============================================================================
# File: src/python/api/v2/database_util/upload_targets.py
# Purpose: SQL for GET /v2/me/upload-targets. Reads mappings through the
#          v_collection_provider view so it works before and after M:N mappings.
# ==============================================================================
from typing import Any, Dict, List, Optional
from uuid import UUID

from asyncpg import Connection

_SELECT = """
    SELECT c.id AS collection_id, c.short_name AS collection_short_name, c.active,
           c.provider_id AS primary_provider_id,
           g.id AS ngroup_id, g.short_name AS ngroup_short_name,
           p.id AS provider_id, p.short_name AS provider_short_name,
           p.long_name AS provider_long_name, p.can_upload
"""

_JOINS = """
    JOIN collection c ON c.id = vcp.collection_id AND c.is_deleted = FALSE
    JOIN provider  p ON p.id = vcp.provider_id
    JOIN ngroup    g ON g.id = c.ngroup_id
"""

_ORDER = " ORDER BY c.short_name, p.short_name;"


async def list_all_target_rows(conn: Connection) -> List[Dict[str, Any]]:
    """Admin: every non-deleted collection with its mapped providers."""
    query = _SELECT + " FROM v_collection_provider vcp " + _JOINS + _ORDER
    return await conn.fetch(query)


async def list_ngroup_target_rows(conn: Connection, ngroup_ids: List[UUID]) -> List[Dict[str, Any]]:
    """DAAC-wide roles and proxy keys: every non-deleted collection in the given DAACs."""
    query = (_SELECT + " FROM v_collection_provider vcp " + _JOINS
             + " WHERE c.ngroup_id = ANY($1::uuid[])" + _ORDER)
    return await conn.fetch(query, ngroup_ids)


async def list_assigned_target_rows(conn: Connection, user_id: UUID, ngroup_ids: List[UUID]) -> List[Dict[str, Any]]:
    """Data Providers: only collections mapped to providers the user is assigned to, within their DAACs."""
    query = (_SELECT + """
    FROM cueuser_provider up
    JOIN v_collection_provider vcp ON vcp.provider_id = up.provider_id
    """ + _JOINS + " WHERE up.cueuser_id = $1 AND c.ngroup_id = ANY($2::uuid[])" + _ORDER)
    return await conn.fetch(query, user_id, ngroup_ids)


async def get_user_name(conn: Connection, user_id: UUID) -> Optional[str]:
    return await conn.fetchval("SELECT name FROM cueuser WHERE id = $1", user_id)


async def get_ngroup(conn, ngroup_id):
    """The DAAC's id and short name (for an API key's caller info)."""
    return await conn.fetchrow("SELECT id, short_name FROM ngroup WHERE id = $1", ngroup_id)
