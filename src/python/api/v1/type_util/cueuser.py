# type_util/cueuser.py
from datetime import datetime
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from typing import Dict


class CueuserBase(BaseModel):
    email: EmailStr
    name: str
    cueusername: str
    edpub_id: Optional[str] = None


class CueuserCreate(CueuserBase):
    ngroup_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None
    role_id: Optional[UUID] = None

    @model_validator(mode="before")
    def none_to_null(cls, values: Dict) -> Dict:
        return {k: (None if v == "" else v) for k, v in values.items()}


class CueuserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    edpub_id: Optional[str] = None
    ngroup_id: Optional[UUID] = None  
    provider_id: Optional[UUID] = None  
    role_id: Optional[UUID] = None  

    @model_validator(mode="before")
    def none_to_null(cls, values: Dict) -> Dict:
        return {k: (None if v == "" else v) for k, v in values.items()}
    


class CueuserReturn(CueuserBase):
    id: UUID  
    ngroup_id: Optional[UUID] = None  
    provider_id: Optional[UUID] = None  
    role_id: Optional[UUID] = None  
    role_short_name: Optional[str] = None  
    role_long_name: Optional[str] = None  
    registered: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: tuple) -> "CueuserReturn":
        return cls(
            id=row['id'],
            email=row['email'],
            name=row['name'],
            cueusername=row['cueusername'],
            edpub_id=row['edpub_id'],
            ngroup_id=row['ngroup_id'],  
            provider_id=row['provider_id'],  
            role_id=row['role_id'],  
            role_short_name=row['role_short_name'],  
            role_long_name=row['role_long_name'],  
            registered=row['registered']
        )


class CueuserRoleReturn(BaseModel):
    role_id: Optional[UUID] = None
    short_name: Optional[str] = None
    long_name: Optional[str] = None