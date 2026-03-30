from pydantic import BaseModel
from typing import Literal
from uuid import UUID

class AthenaQueryDetails(BaseModel):
    current_state: Literal["SUCCEEDED", "FAILED"]
    query_id: str
    user_id: UUID
