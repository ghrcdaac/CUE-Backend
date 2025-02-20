from typing import Optional, Literal

from pydantic import BaseModel, Field



class AuthResponse(BaseModel):
    access_token: str
    id_token: str
    refresh_token: Optional[str] = None
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(..., description="Token expiry time in seconds")

class RefreshTokenRequest(BaseModel):
    refresh_token: str