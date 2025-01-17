from pydantic import BaseModel, UUID4, field_validator
from typing import Dict, Any, Tuple
from uuid import UUID
import json

class EgressCreate(BaseModel):
    type: str
    path: str
    config: Dict[str, Any]
    ngroup_id: UUID

class EgressReturn(EgressCreate):
    id: UUID4

    @classmethod
    def from_db_row(cls, row: Tuple) -> "EgressReturn":
        """Factory function to create an EgressReturn instance from a database row."""
        id, type, path, config_str, ngroup_id = row
        # Parse the JSON string back into a dictionary
        config = json.loads(config_str)
        return cls(id=id, type=type, path=path, config=config, ngroup_id=ngroup_id)

class EgressUpdate(BaseModel):
    type: str | None = None
    path: str | None = None
    config: Dict[str, Any] | None = None
    ngroup_id: UUID | None = None