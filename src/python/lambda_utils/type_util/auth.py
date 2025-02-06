from pydantic import BaseModel, SecretStr
from typing import Optional

class login(BaseModel):
    username: str
    password: SecretStr
    
class pwd_response(BaseModel):
    username: str
    password: SecretStr
    session: str

class auth_response(BaseModel):
    access_token: Optional[str] = None
    session: Optional[str] = None
