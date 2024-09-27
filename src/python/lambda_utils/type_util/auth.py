from pydantic import BaseModel

class auth_token(BaseModel):
    access_token: str
    refresh_token: str
    id_token: str