# File: src/python/api/v2/type_util/archive.py

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from .file_metrics import MetricsQueryParameters
from .file import FileResponse

class ArchiveQueryRequest(MetricsQueryParameters):
    """Request body for starting an archive query. Filters are inherited."""
    pass

class ArchiveQueryStartResponse(BaseModel):
    query_execution_id: str

class ArchiveQueryStatusResponse(BaseModel):
    status: str
    reason: str | None = None

class ArchiveQueryResult(FileResponse):
    ngroup_id: UUID
    metric_upload_at: Optional[str] = None
    aws_transfer_cost: Optional[Decimal] = None
    scanner_cost: Optional[Decimal] = None

class ArchiveQueryResultsResponse(BaseModel):
    items: List[ArchiveQueryResult]