# --- src/python/event_lambdas/infected_logger/model.py ---
import logging
from datetime import datetime, timezone
from typing import List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ValidationError

logger = logging.getLogger(__name__)

class ScanResultDetail(BaseModel):
    """Pydantic model for the detailed scan results within the message."""
    result: str
    virus_name: List[str] = Field(..., alias="virusName")
    message: List[str]
    date_scanned: datetime = Field(..., alias="dateScanned")
    engine: str
    
    @field_validator('date_scanned', mode='before')
    @classmethod
    def parse_datetime(cls, value: Any) -> datetime:
        """Custom parser to handle the specific timestamp format from SNS."""
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.rstrip('Z')).replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error(f"Could not parse timestamp string: {value}")
                raise
        return value

class ScanResultMessage(BaseModel):
    """
    Pydantic model for the main content of the SNS message.
    Validates required fields and their types.
    """
    key: UUID  # Changed from 'id' to 'key'
    result: str
    date_scanned: datetime = Field(..., alias="dateScanned")
    scan_results: Optional[List[ScanResultDetail]] = Field(None, alias="scanResults")

    @field_validator('date_scanned', mode='before')
    @classmethod
    def parse_datetime(cls, value: Any) -> datetime:
        """Re-use the same timestamp parser for the top-level dateScanned field."""
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.rstrip('Z')).replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error(f"Could not parse timestamp string: {value}")
                raise
        return value

def parse_and_validate_message(message_content: dict) -> Optional[ScanResultMessage]:
    """
    Factory function to parse a raw dictionary into a validated Pydantic model.
    """
    try:
        return ScanResultMessage.model_validate(message_content)
    except ValidationError as e:
        # Use .get() for safer access in case the key is missing entirely
        file_key = message_content.get('key', 'N/A')
        logger.error(f"SNS message validation failed for file key {file_key}: {e}", exc_info=True)
        return None
