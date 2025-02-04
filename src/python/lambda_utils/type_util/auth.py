from pydantic import BaseModel, SecretStr

class login(BaseModel):
    username: str
    password: SecretStr

class auth_token(BaseModel):
    access_token: str
    refresh_token: str
    id_token: str