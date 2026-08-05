from pydantic import BaseModel
from typing import List
from uuid import UUID 

class Event(BaseModel):
    file_ids: List[UUID]