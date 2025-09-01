from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

class AthenaQueryDetail(BaseModel):
    """Pydantic model for the 'detail' object of an Athena State Change event."""
    current_state: str = Field(..., alias="currentState")
    query_execution_id: str = Field(..., alias="queryExecutionId")

def parse_and_validate_event_detail(event_detail: dict) -> Optional[AthenaQueryDetail]:
    """Factory function to parse the event detail into a validated model."""
    try:
        return AthenaQueryDetail.model_validate(event_detail)
    except ValidationError as e:
        logger.error("event.detail.validation_failed", detail=event_detail, error=str(e))
        return None
