from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional
from .models import UserType

class RegisterRequest(BaseModel):
    email: str
    password: str
    user_type: UserType
    # Type-specific fields — only validated for the relevant type
    full_name: Optional[str] = None      # customer
    company_name: Optional[str] = None  # vendor
    department: Optional[str] = None    # admin

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserOut(BaseModel):
    id: UUID
    email: str
    user_type: UserType
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True

class DeactivateRequest(BaseModel):
    user_id: UUID
