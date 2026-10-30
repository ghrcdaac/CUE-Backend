# ==============================================================================
# File: src/python/api/v2/database_util/mapping_history.py
# Purpose: Permanent audit rows for collection_provider and cueuser_provider changes.
#          Call inside the same transaction as the mapping change.
# ==============================================================================
import json
from typing import Any, Dict, Iterable, Optional
from uuid import UUID

from asyncpg import Connection

COLLECTION_PROVIDER = "collection_provider"
CUEUSER_PROVIDER = "cueuser_provider"

_INSERT = """
    INSERT INTO mapping_history (mapping_type, left_id, right_id, action, actor_id, details)
    VALUES ($1, $2, $3, $4, $5, $6::jsonb)
"""


def _actor(actor_id: Optional[Any]) -> Optional[UUID]:
    if actor_id is None:
        return None
    return actor_id if isinstance(actor_id, UUID) else UUID(str(actor_id))


async def record(conn: Connection, mapping_type: str, left_id: UUID, right_id: UUID, action: str,
                 actor_id: Optional[Any], details: Optional[Dict[str, Any]] = None) -> None:
    await conn.execute(_INSERT, mapping_type, left_id, right_id, action, _actor(actor_id),
                       json.dumps(details) if details is not None else None)


async def record_many(conn: Connection, mapping_type: str, left_id: UUID, right_ids: Iterable[UUID], action: str,
                      actor_id: Optional[Any], details: Optional[Dict[str, Any]] = None) -> None:
    rows = [(mapping_type, left_id, rid, action, _actor(actor_id),
             json.dumps(details) if details is not None else None) for rid in right_ids]
    if rows:
        await conn.executemany(_INSERT, rows)
