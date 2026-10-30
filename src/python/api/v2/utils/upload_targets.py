# ==============================================================================
# File: src/python/api/v2/utils/upload_targets.py
# Purpose: Logic for GET /v2/me/upload-targets (collections the caller can upload to).
# ==============================================================================
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import Request

from v2.database_util import upload_targets as targets_db
from v2.type_util.auth import AuthUser

logger = structlog.get_logger(__name__)

# Roles that may upload to every collection in their DAACs (owner decision Q15).
NGROUP_WIDE_UPLOAD_ROLES = {"daac_manager", "daac_staff", "security"}


def _scope_for(user: AuthUser) -> str:
    """Which selection rule applies: 'all' (admin), 'ngroups' (DAAC roles, proxy keys), or 'assigned'."""
    roles = set(user.roles or [])
    if "admin" in roles:
        return "all"
    if "proxy" in roles or roles & NGROUP_WIDE_UPLOAD_ROLES:
        return "ngroups"
    return "assigned"


def _ngroup_uuids(user: AuthUser) -> List[UUID]:
    out = []
    for ng in user.ngroups or []:
        try:
            out.append(UUID(str(ng)))
        except ValueError:
            continue
    return out


def group_target_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Folds one-row-per-(collection, provider) into one target per collection, keeping query order."""
    targets: Dict[Any, Dict[str, Any]] = {}
    for r in rows:
        cid = r["collection_id"]
        t = targets.get(cid)
        if t is None:
            t = {
                "collection_id": cid,
                "collection_short_name": r["collection_short_name"],
                "active": bool(r["active"]),
                "ngroup": {"id": r["ngroup_id"], "short_name": r["ngroup_short_name"]},
                "primary_provider_id": r["primary_provider_id"],
                "providers": [],
            }
            targets[cid] = t
        t["providers"].append({
            "id": r["provider_id"],
            "short_name": r["provider_short_name"],
            "long_name": r["provider_long_name"],
            "can_upload": bool(r["can_upload"]),
        })

    for t in targets.values():
        reasons = []
        if not t["active"]:
            reasons.append("collection_inactive")
        if not any(p["can_upload"] for p in t["providers"]):
            reasons.append("provider_uploads_disabled")
        t["reasons"] = reasons
        t["uploadable"] = not reasons
    return list(targets.values())


def filter_targets(targets: List[Dict[str, Any]], include_unavailable: bool, search: Optional[str]) -> List[Dict[str, Any]]:
    if not include_unavailable:
        targets = [t for t in targets if t["uploadable"]]
    if search:
        needle = search.lower()
        targets = [
            t for t in targets
            if needle in t["collection_short_name"].lower()
            or any(needle in (p["short_name"] or "").lower() for p in t["providers"])
        ]
    return targets


def _caller_info(auth_kind: str, user: AuthUser, key_info: Optional[Dict[str, Any]], db_name: Optional[str]) -> Dict[str, Any]:
    if auth_kind == "api_key" and key_info is not None:
        is_proxy = key_info.get("key_type") == "proxy" or not key_info.get("user_id")
        return {
            "auth_kind": "api_key",
            "name": key_info.get("name") if is_proxy else user.name,
            "key": {
                "name": key_info.get("name"),
                "suffix": key_info.get("key_display_suffix"),
                "expires_at": key_info.get("expires_at"),
                "scopes": list(key_info.get("scopes") or []),
                "type": str(key_info["key_type"]) if key_info.get("key_type") else None,
            },
        }
    return {"auth_kind": "jwt", "name": db_name or user.name, "key": None}


async def list_upload_targets(
    request: Request, user: AuthUser, include_unavailable: bool = False, search: Optional[str] = None
) -> Dict[str, Any]:
    auth_kind = getattr(request.state, "auth_kind", "jwt")
    key_info = getattr(request.state, "api_key_info", None)
    scope = _scope_for(user)
    db_name = None

    async with request.state.pool.acquire() as conn:
        if scope == "all":
            rows = await targets_db.list_all_target_rows(conn)
        elif scope == "ngroups":
            rows = await targets_db.list_ngroup_target_rows(conn, _ngroup_uuids(user))
        else:
            rows = await targets_db.list_assigned_target_rows(conn, user.id, _ngroup_uuids(user))
        if auth_kind == "jwt":
            db_name = await targets_db.get_user_name(conn, user.id)

    targets = filter_targets(group_target_rows(rows), include_unavailable, search)
    logger.info("upload_targets.listed", user_id=str(user.id), auth_kind=auth_kind, count=len(targets))
    return {
        "generated_at": datetime.now(timezone.utc),
        "auth_kind": auth_kind,
        "caller": _caller_info(auth_kind, user, key_info, db_name),
        "targets": targets,
    }
