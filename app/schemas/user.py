"""User Pydantic schemas. FR-AUTH-003."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    role: str = Field(..., pattern="^(Admin|Project Manager|Site Engineer|Viewer)$")
    phone: str | None = None
    profile_picture: str | None = None


class UserCreate(UserBase):
    """Admin creates user. Auth is mobile OTP only (no password)."""


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    role: str | None = Field(None, pattern="^(Admin|Project Manager|Site Engineer|Viewer)$")
    phone: str | None = None
    profile_picture: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    phone: str | None = None
    is_active: bool

    class Config:
        from_attributes = True
