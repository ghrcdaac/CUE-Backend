from typing import Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, EmailStr, validator
import re  


class AuthResponse(BaseModel):
    access_token: str
    id_token: str
    refresh_token: Optional[str] = None
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(..., description="Token expiry time in seconds")


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    username: str  # Could also be EmailStr


class ConfirmForgotPasswordRequest(BaseModel):
    username: str
    confirmation_code: str
    new_password: str

    @validator("new_password")
    def password_strength(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search("[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search("[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search("[0-9]", value):
            raise ValueError("Password must contain at least one number")
        if not re.search("[^a-zA-Z0-9\s]", value): # Check for special characters (excluding spaces)
            raise ValueError("Password must contain at least one special character")
        return value


class ChangePasswordRequest(BaseModel):
    previous_password: str
    new_password: str

    @validator("new_password")
    def password_strength(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search("[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search("[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search("[0-9]", value):
            raise ValueError("Password must contain at least one number")
        if not re.search("[^a-zA-Z0-9\s]", value): # Check for special characters (excluding spaces)
            raise ValueError("Password must contain at least one special character")
        return value