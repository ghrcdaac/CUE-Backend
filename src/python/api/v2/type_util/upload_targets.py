# ==============================================================================
# File: src/python/api/v2/type_util/upload_targets.py
# Purpose: Pydantic models for GET /v2/me/upload-targets (desktop app dropdown).
# ==============================================================================
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

UploadTargetReason = Literal["collection_inactive", "provider_uploads_disabled"]


class UploadTargetNgroup(BaseModel):
    id: UUID
    short_name: str


class UploadTargetProvider(BaseModel):
    id: UUID
    short_name: str
    long_name: Optional[str] = None
    can_upload: bool


class UploadTarget(BaseModel):
    collection_id: UUID
    collection_short_name: str
    active: bool
    ngroup: UploadTargetNgroup
    primary_provider_id: Optional[UUID] = None
    providers: List[UploadTargetProvider]
    uploadable: bool
    reasons: List[UploadTargetReason]


class CallerKeyInfo(BaseModel):
    """Non-secret metadata of the API key used for the call."""
    name: Optional[str] = None
    suffix: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: List[str] = []
    type: Optional[str] = None


class CallerInfo(BaseModel):
    auth_kind: Literal["jwt", "api_key"]
    name: Optional[str] = None
    key: Optional[CallerKeyInfo] = None


class UploadTargetsResponse(BaseModel):
    generated_at: datetime
    auth_kind: Literal["jwt", "api_key"]
    caller: CallerInfo
    targets: List[UploadTarget]
