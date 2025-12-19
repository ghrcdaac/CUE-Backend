from pydantic import BaseModel
from typing import List
from uuid import UUID

class RedrivePayload(BaseModel):
    file_ids: List[UUID]
    user_id: UUID