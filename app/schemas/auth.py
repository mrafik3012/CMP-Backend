"""Auth schemas. FR-AUTH-001, FR-AUTH-002, FR-AUTH-004. Mobile OTP only."""
from typing import Literal
from pydantic import BaseModel, Field


class SendLoginOtpRequest(BaseModel):
    """Request OTP for login. Phone with country code (e.g. +91 9876543210)."""
    phone: str = Field(..., min_length=10, max_length=20)


class VerifyLoginOtpRequest(BaseModel):
    """Verify OTP and log in. Remember Me = skip re-login for 7 days."""
    phone: str = Field(..., min_length=10, max_length=20)
    otp: str = Field(..., min_length=6, max_length=6)
    remember_me: bool = False


class VerifySignupOtpRequest(BaseModel):
    """Verify signup OTP (phone + 6-digit code) → activate account and log in."""
    phone: str = Field(..., min_length=10, max_length=20)
    otp: str = Field(..., min_length=6, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RegisterRequest(BaseModel):
    """Signup: phone mandatory, email optional. No password (auth via mobile OTP)."""
    name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=10, max_length=20)
    email: str | None = Field(None, max_length=255)
    role: Literal[
        "contractor",
        "homeowner",
        "architect",
        "subcontractor",
        "project_manager",
        "consultant",
    ]
