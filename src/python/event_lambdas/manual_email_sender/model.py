from pydantic import BaseModel, Field
from typing import List
from uuid import UUID

class EmailPayload(BaseModel):
    recipients:List[str] = Field(..., min_length=1)
    subject:str = Field(min_length=1)
    body_html:str = Field(min_length=1)
    body_text:str = Field(min_length=1)
    user_id: UUID