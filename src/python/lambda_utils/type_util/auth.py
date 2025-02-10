from pydantic import BaseModel, SecretStr
from typing import Optional, Dict, List

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
    
# Bearer types

JWK = Dict[str, str]

class JWKS(BaseModel):
    keys: List[JWK]
    
class JWTAuthorizationCredentials(BaseModel):
    jwt_token: str
    header: Dict
    claims: Dict
    signature: str
    message: str
