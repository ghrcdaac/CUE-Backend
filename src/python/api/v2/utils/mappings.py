# ==============================================================================
# File: src/python/api/v2/utils/mappings.py
# Purpose: Many-to-many mapping CRUD (collection <-> provider, user <-> provider)
#          with audit rows in mapping_history (plan 11 B3). Every write runs in one
#          transaction together with its history rows.
# Rule (owner decision Q17): mappings never cross DAACs, for anyone, admins included.
# ==============================================================================
import json
from typing import Any, Dict, Iterable, List, Optional, Set
from uuid import UUID

import structlog
from fastapi import Request

from v2.database_util import collection as collection_db
from v2.database_util import collection_provider as cp_db
from v2.database_util import cueuser as user_db
from v2.database_util import cueuser_provider as up_db
from v2.database_util import mapping_history as history
from v2.database_util import provider as provider_db
from v2.type_util.auth import AuthUser

logger = structlog.get_logger(__name__)


class MappingError(Exception):
    status_code = 400


class MappingBadRequest(MappingError):
    status_code = 400


class MappingForbidden(MappingError):
    status_code = 403


class MappingNotFound(MappingError):
    status_code = 404


class MappingConflict(MappingError):
    status_code = 409


SAME_DAAC_MESSAGE = "Provider and collection must belong to the same DAAC."


def _is_admin(user: AuthUser) -> bool:
    return "admin" in (user.roles or [])


def _user_ngroups(user: AuthUser) -> Set[str]:
    out = set()
    for ng in user.ngroups or []:
        out.add(str(ng["id"]) if isinstance(ng, dict) else str(ng))
    return out


def assert_same_ngroup(collection_ngroup_id: Any, providers: Iterable[Dict[str, Any]]) -> None:
    """Every provider must be in the collection's DAAC (applies to admins too)."""
    for p in providers:
        if str(p["ngroup_id"]) != str(collection_ngroup_id):
            raise MappingBadRequest(SAME_DAAC_MESSAGE)


async def _get_collection(conn, collection_id: UUID, user: AuthUser) -> Dict[str, Any]:
    collection = await collection_db.get_collection_by_id(conn, collection_id)
    if not collection:
        raise MappingNotFound(f"Collection not found with ID: {collection_id}")
    if not _is_admin(user) and str(collection["ngroup_id"]) not in _user_ngroups(user):
        raise MappingForbidden("Access denied. Collection is not in your DAAC.")
    return dict(collection)


async def _get_providers(conn, provider_ids: Iterable[UUID]) -> List[Dict[str, Any]]:
    out = []
    for pid in provider_ids:
        p = await provider_db.get_provider_by_id(conn, pid)
        if not p:
            raise MappingNotFound(f"Provider not found with ID: {pid}")
        out.append(dict(p))
    return out


def collection_mapping(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "provider_id": row["provider_id"], "short_name": row["short_name"], "long_name": row["long_name"],
        "can_upload": row["can_upload"], "is_primary": bool(row["is_primary"]),
    }


# ------------------------------------------------------------------------------
# Collection <-> provider
# ------------------------------------------------------------------------------

async def list_collection_providers(request: Request, user: AuthUser, collection_id: UUID) -> List[Dict[str, Any]]:
    async with request.state.pool.acquire() as conn:
        await _get_collection(conn, collection_id, user)
        rows = await cp_db.list_providers_for_collection(conn, collection_id)
    return [collection_mapping(r) for r in rows]


async def add_collection_provider(request: Request, user: AuthUser, collection_id: UUID, provider_id: UUID):
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            collection = await _get_collection(conn, collection_id, user)
            providers = await _get_providers(conn, [provider_id])
            assert_same_ngroup(collection["ngroup_id"], providers)
            if provider_id in await cp_db.mapped_provider_ids(conn, collection_id):
                raise MappingConflict("Provider is already mapped to this collection.")
            await cp_db.add_mapping(conn, collection_id, provider_id, user.id)
            await history.record(conn, history.COLLECTION_PROVIDER, collection_id, provider_id, "added", user.id)
            rows = await cp_db.list_providers_for_collection(conn, collection_id)
    logger.info("mapping.collection_provider.added", collection_id=str(collection_id), provider_id=str(provider_id),
                actor_id=str(user.id))
    return [collection_mapping(r) for r in rows]


async def remove_collection_provider(request: Request, user: AuthUser, collection_id: UUID, provider_id: UUID) -> None:
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            collection = await _get_collection(conn, collection_id, user)
            if str(collection["provider_id"]) == str(provider_id):
                raise MappingBadRequest("This is the primary provider. Set another primary first.")
            if not await cp_db.remove_mapping(conn, collection_id, provider_id):
                raise MappingNotFound("Provider is not mapped to this collection.")
            await history.record(conn, history.COLLECTION_PROVIDER, collection_id, provider_id, "removed", user.id)
    logger.info("mapping.collection_provider.removed", collection_id=str(collection_id), provider_id=str(provider_id),
                actor_id=str(user.id))


async def replace_collection_providers(request: Request, user: AuthUser, collection_id: UUID,
                                       provider_ids: List[UUID]) -> List[Dict[str, Any]]:
    wanted = set(provider_ids)
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            collection = await _get_collection(conn, collection_id, user)
            primary = collection["provider_id"]
            if primary not in wanted:
                raise MappingBadRequest("provider_ids must include the primary provider.")
            providers = await _get_providers(conn, wanted)
            assert_same_ngroup(collection["ngroup_id"], providers)
            current = await cp_db.mapped_provider_ids(conn, collection_id)
            to_add = sorted(wanted - current, key=str)
            to_remove = sorted(current - wanted, key=str)
            for pid in to_add:
                await cp_db.add_mapping(conn, collection_id, pid, user.id)
            # The primary is always kept in the mapping table too.
            await cp_db.add_mapping(conn, collection_id, primary, user.id)
            for pid in to_remove:
                await cp_db.remove_mapping(conn, collection_id, pid)
            await history.record_many(conn, history.COLLECTION_PROVIDER, collection_id, to_add, "added", user.id)
            await history.record_many(conn, history.COLLECTION_PROVIDER, collection_id, to_remove, "removed", user.id)
            rows = await cp_db.list_providers_for_collection(conn, collection_id)
    logger.info("mapping.collection_provider.replaced", collection_id=str(collection_id), added=len(to_add),
                removed=len(to_remove), actor_id=str(user.id))
    return [collection_mapping(r) for r in rows]


async def set_collection_primary(request: Request, user: AuthUser, collection_id: UUID,
                                 provider_id: UUID) -> List[Dict[str, Any]]:
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            collection = await _get_collection(conn, collection_id, user)
            old_primary = collection["provider_id"]
            if provider_id not in await cp_db.mapped_provider_ids(conn, collection_id):
                raise MappingBadRequest("Provider must already be mapped to the collection before it can be primary.")
            if str(old_primary) != str(provider_id):
                # Both stay mapped: the old primary becomes a secondary.
                await cp_db.add_mapping(conn, collection_id, old_primary, user.id)
                await cp_db.add_mapping(conn, collection_id, provider_id, user.id)
                await cp_db.set_primary(conn, collection_id, provider_id)
                await history.record(conn, history.COLLECTION_PROVIDER, collection_id, old_primary, "primary_unset", user.id)
                await history.record(conn, history.COLLECTION_PROVIDER, collection_id, provider_id, "primary_set", user.id)
            rows = await cp_db.list_providers_for_collection(conn, collection_id)
    logger.info("mapping.collection_provider.primary_set", collection_id=str(collection_id),
                provider_id=str(provider_id), actor_id=str(user.id))
    return [collection_mapping(r) for r in rows]


async def list_provider_collections(request: Request, user: AuthUser, provider_id: UUID) -> List[Dict[str, Any]]:
    async with request.state.pool.acquire() as conn:
        provider = await provider_db.get_provider_by_id(conn, provider_id)
        if not provider:
            raise MappingNotFound(f"Provider not found with ID: {provider_id}")
        if not _is_admin(user) and str(provider["ngroup_id"]) not in _user_ngroups(user):
            raise MappingForbidden("Access denied. Provider is not in your DAAC.")
        rows = await cp_db.list_collections_for_provider(conn, provider_id)
    return [{"collection_id": r["collection_id"], "short_name": r["short_name"], "active": r["active"],
             "ngroup_id": r["ngroup_id"], "is_primary": bool(r["is_primary"])} for r in rows]


# --- hooks for the existing (legacy) collection write paths ---

async def on_collection_created(conn, collection_id: UUID, provider_id: UUID, actor_id) -> None:
    await cp_db.add_mapping(conn, collection_id, provider_id, actor_id)
    await history.record(conn, history.COLLECTION_PROVIDER, collection_id, provider_id, "added", actor_id)


async def on_legacy_primary_move(conn, collection_id: UUID, old_provider_id: UUID, new_provider_id: UUID,
                                 actor_id) -> None:
    """Legacy PATCH provider_id A -> B keeps its 'move' meaning: add B, remove A."""
    if str(old_provider_id) == str(new_provider_id):
        return
    details = {"via": "legacy_patch"}
    if await cp_db.add_mapping(conn, collection_id, new_provider_id, actor_id):
        await history.record(conn, history.COLLECTION_PROVIDER, collection_id, new_provider_id, "added", actor_id, details)
    await history.record(conn, history.COLLECTION_PROVIDER, collection_id, new_provider_id, "primary_set", actor_id, details)
    await history.record(conn, history.COLLECTION_PROVIDER, collection_id, old_provider_id, "primary_unset", actor_id, details)
    # The old primary is unmapped even if it was only mapped through collection.provider_id.
    await cp_db.remove_mapping(conn, collection_id, old_provider_id)
    await history.record(conn, history.COLLECTION_PROVIDER, collection_id, old_provider_id, "removed", actor_id, details)


# ------------------------------------------------------------------------------
# User <-> provider
# ------------------------------------------------------------------------------

async def _get_target_user(conn, user_id: UUID, actor: AuthUser) -> Set[str]:
    """Returns the target user's ngroup ids, enforcing that non-admins share a DAAC with them."""
    record = await user_db.get_user_by_id(conn, user_id)
    if not record:
        raise MappingNotFound(f"User not found with ID: {user_id}")
    ngroups = record["ngroups"]
    if isinstance(ngroups, str):
        ngroups = json.loads(ngroups)
    target_ngroups = {str(ng["id"]) for ng in ngroups or [] if "id" in ng}
    if not _is_admin(actor) and not (target_ngroups & _user_ngroups(actor)):
        raise MappingForbidden("Access denied. You don't share a DAAC with this user.")
    return target_ngroups


def _assert_provider_in_user_ngroups(providers: Iterable[Dict[str, Any]], target_ngroups: Set[str]) -> None:
    for p in providers:
        if str(p["ngroup_id"]) not in target_ngroups:
            raise MappingBadRequest("Provider must belong to one of the user's DAACs.")


def _user_mapping(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"provider_id": row["provider_id"], "short_name": row["short_name"], "long_name": row["long_name"],
            "can_upload": row["can_upload"], "ngroup_id": row["ngroup_id"]}


async def list_user_providers(request: Request, actor: AuthUser, user_id: UUID) -> List[Dict[str, Any]]:
    async with request.state.pool.acquire() as conn:
        await _get_target_user(conn, user_id, actor)
        rows = await up_db.list_user_providers(conn, user_id)
    return [_user_mapping(r) for r in rows]


async def add_user_provider(request: Request, actor: AuthUser, user_id: UUID, provider_id: UUID):
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            target_ngroups = await _get_target_user(conn, user_id, actor)
            _assert_provider_in_user_ngroups(await _get_providers(conn, [provider_id]), target_ngroups)
            if not await up_db.add_user_provider(conn, user_id, provider_id):
                raise MappingConflict("User is already assigned to this provider.")
            await history.record(conn, history.CUEUSER_PROVIDER, user_id, provider_id, "added", actor.id)
            rows = await up_db.list_user_providers(conn, user_id)
    logger.info("mapping.cueuser_provider.added", user_id=str(user_id), provider_id=str(provider_id),
                actor_id=str(actor.id))
    return [_user_mapping(r) for r in rows]


async def remove_user_provider(request: Request, actor: AuthUser, user_id: UUID, provider_id: UUID) -> None:
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            await _get_target_user(conn, user_id, actor)
            if not await up_db.remove_user_provider(conn, user_id, provider_id):
                raise MappingNotFound("User is not assigned to this provider.")
            await history.record(conn, history.CUEUSER_PROVIDER, user_id, provider_id, "removed", actor.id)
    logger.info("mapping.cueuser_provider.removed", user_id=str(user_id), provider_id=str(provider_id),
                actor_id=str(actor.id))


async def replace_user_providers(request: Request, actor: AuthUser, user_id: UUID,
                                 provider_ids: List[UUID]) -> List[Dict[str, Any]]:
    wanted = set(provider_ids)
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            target_ngroups = await _get_target_user(conn, user_id, actor)
            _assert_provider_in_user_ngroups(await _get_providers(conn, wanted), target_ngroups)
            current = await up_db.user_provider_ids(conn, user_id)
            to_add = sorted(wanted - current, key=str)
            to_remove = sorted(current - wanted, key=str)
            for pid in to_add:
                await up_db.add_user_provider(conn, user_id, pid)
            for pid in to_remove:
                await up_db.remove_user_provider(conn, user_id, pid)
            await history.record_many(conn, history.CUEUSER_PROVIDER, user_id, to_add, "added", actor.id)
            await history.record_many(conn, history.CUEUSER_PROVIDER, user_id, to_remove, "removed", actor.id)
            rows = await up_db.list_user_providers(conn, user_id)
    logger.info("mapping.cueuser_provider.replaced", user_id=str(user_id), added=len(to_add),
                removed=len(to_remove), actor_id=str(actor.id))
    return [_user_mapping(r) for r in rows]
