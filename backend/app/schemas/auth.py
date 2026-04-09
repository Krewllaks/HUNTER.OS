"""
HUNTER.OS - Auth Schemas
"""
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 900  # seconds (15 min default)


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    plan: str = "trial"
    is_active: bool

    model_config = {"from_attributes": True}
