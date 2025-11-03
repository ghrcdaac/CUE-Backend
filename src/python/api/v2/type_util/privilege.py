from pydantic import BaseModel
from typing import Optional, Tuple

class PrivilegeBase(BaseModel):
    privilege: str

class PrivilegeCreate(PrivilegeBase):
    pass

class PrivilegeUpdate(BaseModel):
    privilege: Optional[str] = None  # Making it optional for updates

class PrivilegeReturn(PrivilegeBase):
    @classmethod
    def from_db_row(cls, row: Tuple) -> "PrivilegeReturn":
        privilege = row[0]  # Adjust according to table structure
        return cls(privilege=privilege)