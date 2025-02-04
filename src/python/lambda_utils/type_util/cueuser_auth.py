from pydantic import BaseModel, UUID4
from typing import Tuple
from datetime import datetime

class CueuserAuthCreate(BaseModel):
    id: UUID4  # This is the same as the cueuser ID (foreign key)
    refresh_token: str

class CueuserAuthUpdate(BaseModel):
    refresh_token: str

class CueuserAuthReturn(BaseModel):
    id: UUID4
    refresh_token: str
    last_login: datetime

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserAuthReturn":
        id, refresh_token, last_login = row
        return cls(id=id, refresh_token=refresh_token, last_login=last_login)