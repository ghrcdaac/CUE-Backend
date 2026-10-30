# ==============================================================================
# File: src/python/api/v2/endpoints/upload_targets.py
# Purpose: GET /v2/me/upload-targets - collections the caller can upload to.
#          Accepts a Keycloak JWT OR a cue_sk_ API key with 'file:upload'.
# ==============================================================================
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from core.security import JWTOrAPIKeyBearer
from v2.type_util.auth import AuthUser
from v2.type_util.upload_targets import UploadTargetsResponse
from v2.utils import upload_targets as targets_utils

router = APIRouter(prefix="/me", tags=["V2 - Upload targets (desktop app)"])

jwt_or_upload_key = JWTOrAPIKeyBearer(required_scopes=["file:upload"])


@router.get("/upload-targets", response_model=UploadTargetsResponse)
async def list_my_upload_targets(
    request: Request,
    include_unavailable: bool = Query(False, description="Also return collections that can't accept uploads right now."),
    search: Optional[str] = Query(None, max_length=100, description="Substring of a collection or provider short name."),
    user: AuthUser = Depends(jwt_or_upload_key),
):
    """Collections the caller can upload to, with their providers, plus non-secret caller info."""
    data = await targets_utils.list_upload_targets(request, user, include_unavailable, search)
    return UploadTargetsResponse.model_validate(data)
