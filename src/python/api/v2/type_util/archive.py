# File: src/python/api/v2/type_util/archive.py

from pydantic import BaseModel, Field
from typing import List
from uuid import UUID
from .file_metrics import MetricsQueryParameters
from .file import FileResponse # Re-use the rich file response model

class ArchiveQueryRequest(MetricsQueryParameters):
    """Request body for starting an archive query. Filters are inherited."""
    pass

class ArchiveQueryStartResponse(BaseModel):
    query_execution_id: str

class ArchiveQueryStatusResponse(BaseModel):
    status: str
    reason: str | None = None

class ArchiveQueryResultsResponse(BaseModel):
    items: List[FileResponse]