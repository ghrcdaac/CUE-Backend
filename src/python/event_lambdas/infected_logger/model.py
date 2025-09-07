import structlog
from datetime import datetime, timezone
from typing import List, Optional, Any
from uuid import UUID
import json

from pydantic import BaseModel, Field, field_validator, ValidationError

logger = structlog.get_logger(__name__)

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
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.rstrip('Z')).replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error("pydantic.validation.timestamp_parse_error", value=value)
                raise
        return value

class ScanResultMessage(BaseModel):
    """Pydantic model for the main content of the SNS message."""
    key: UUID
    result: str
    date_scanned: datetime = Field(..., alias="dateScanned")
    scan_results: Optional[List[ScanResultDetail]] = Field(None, alias="scanResults")

    @field_validator('date_scanned', mode='before')
    @classmethod
    def parse_datetime(cls, value: Any) -> datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.rstrip('Z')).replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error("pydantic.validation.timestamp_parse_error", value=value)
                raise
        return value

def parse_and_validate_message(message_content: dict) -> Optional[ScanResultMessage]:
    """Factory function to parse a raw dictionary into a validated Pydantic model."""
    try:
        return ScanResultMessage.model_validate(message_content)
    except ValidationError as e:
        file_key = message_content.get('key', 'N/A')
        logger.error("sns.message.validation_failed", file_key=file_key, exc_info=True)
        return None

class ScanResultDetailJSONEncoder(json.JSONEncoder):
    """JSONEncoder class to serialize ScanResultDetails into JSON strings""" 
    def default(self, obj):
        if isinstance(obj, datetime):
           return obj.strftime("%Y-%m-%dT%H:%M:%S%fZ")
        return super().default(obj)