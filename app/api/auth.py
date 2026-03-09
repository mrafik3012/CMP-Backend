from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Any

# FIXED - use get_settings()
from app.core.config import get_settings
settings = get_settings()

from app.core.deps import get_current_user, RequireAdmin
from app.db.session import get_db
from app.schemas.auth import (
    TokenResponse,
    RegisterRequest,
    SendLoginOtpRequest,
    VerifyLoginOtpRequest,
    VerifySignupOtpRequest,
)
from app.services.auth_service import (
    create_tokens_for_user,
    refresh_access_token,
    register_user,
    send_login_otp_to_user,
    verify_login_otp_and_get_user,
    verify_signup_otp,
)
from app.services.user_service import get_user_by_id
from app.db.models import User, RefreshToken
from app.core.security import decode_token
import hashlib

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/ping")
def auth_ping():
    """Verify auth API is mounted. Returns 200."""
    return {"status": "ok", "message": "auth API"}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def set_token_cookies(
    response: Response, tokens: TokenResponse, remember_me: bool | None = None
) -> None:
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60
    )
    if remember_me is None:
        refresh_days = settings.refresh_token_expire_days
    elif remember_me:
        refresh_days = settings.refresh_token_expire_days_long
    else:
        refresh_days = settings.refresh_token_expire_days_short

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=refresh_days * 24 * 3600,
    )

@router.get("/debug-otp-db")
def debug_otp_db(db: Session = Depends(get_db)):
    """Dev only: list users (email, phone) and DB path to verify OTP lookup. No auth."""
    from app.core.config import get_settings
    users = db.query(User).all()
    return {
        "database_url": get_settings().database_url,
        "users": [
            {"id": u.id, "email": u.email, "phone": u.phone, "is_active": u.is_active}
            for u in users
        ],
    }


@router.post("/send-login-otp")
def send_login_otp(data: SendLoginOtpRequest, db: Session = Depends(get_db)):
    """Send 6-digit OTP to user's phone (SMS/email fallback). Primary login flow."""
    import logging
    logging.getLogger(__name__).info("send_login_otp request phone=%r", data.phone)
    result = send_login_otp_to_user(db, data.phone)
    if "error" in result:
        # 400 = phone not registered (so 404 = route really not found)
        status = 400 if result["error"] == "phone_not_found" else 403
        raise HTTPException(status_code=status, detail=result["error"])
    return result

@router.post("/verify-login-otp", response_model=TokenResponse)
def verify_login_otp(
    data: VerifyLoginOtpRequest, response: Response, db: Session = Depends(get_db)
):
    """Verify OTP and log in. Remember Me = 7-day session."""
    tokens = verify_login_otp_and_get_user(
        db, data.phone, data.otp, data.remember_me
    )
    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    from app.core.otp_sender import normalize_phone
    user = db.query(User).filter(User.phone == normalize_phone(data.phone)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    refresh_days = (
        settings.refresh_token_expire_days_long
        if data.remember_me
        else settings.refresh_token_expire_days_short
    )
    expires_at = datetime.utcnow() + timedelta(days=refresh_days)
    token_hash = _hash_token(tokens.refresh_token)
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()

    set_token_cookies(response, tokens, remember_me=data.remember_me)
    return tokens

def get_refresh_token(request: Request) -> str | None:
    return (request.cookies.get("refresh_token") or 
            request.headers.get("Authorization", "").replace("Bearer ", ""))

@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, request: Request, db: Session = Depends(get_db)):
    """FR-AUTH-002: Refresh access token"""
    refresh_token = get_refresh_token(request)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    token_hash = _hash_token(refresh_token)
    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    tokens = refresh_access_token(db, refresh_token)
    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old token record and create a new one (rotation)
    db_token.revoked = True
    db.commit()

    payload = decode_token(tokens.refresh_token)
    remember_me_flag = None
    refresh_days = settings.refresh_token_expire_days
    if payload is not None and "remember_me" in payload:
        remember_me_flag = bool(payload["remember_me"])
        refresh_days = (
            settings.refresh_token_expire_days_long
            if remember_me_flag
            else settings.refresh_token_expire_days_short
        )

    new_hash = _hash_token(tokens.refresh_token)
    new_db_token = RefreshToken(
        user_id=db_token.user_id,
        token_hash=new_hash,
        expires_at=datetime.utcnow() + timedelta(days=refresh_days),
    )
    db.add(new_db_token)
    db.commit()

    set_token_cookies(response, tokens, remember_me=remember_me_flag)
    return tokens

@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    """FR-AUTH-003: Clear tokens"""
    refresh_token = get_refresh_token(request)
    if refresh_token:
        token_hash = _hash_token(refresh_token)
        db_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False))
            .first()
        )
        if db_token:
            db_token.revoked = True
            db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}

# Phone OTP only; email verification not used
@router.post("/verify-phone", response_model=TokenResponse)
def verify_phone(otp: str, response: Response, db: Session = Depends(get_db)):
    """Verify phone OTP → activate → tokens!"""
    user = db.query(User).filter(
        User.phone_otp_hash.is_not(None),
        User.otp_expires_at > datetime.utcnow()
    ).order_by(User.id.desc()).first()
    
    if not user or not pwd_context.verify(otp, user.phone_otp_hash):
        raise HTTPException(status_code=400, detail="❌ Invalid/expired phone code")
    
    # Activate account
    user.is_phone_verified = True
    user.phone_otp_hash = None
    user.is_active = True
    db.commit()
    
    tokens = create_tokens_for_user(user)
    set_token_cookies(response, tokens)
    return tokens

@router.post("/verify-signup-otp", response_model=TokenResponse)
def verify_signup_otp_endpoint(
    data: VerifySignupOtpRequest, response: Response, db: Session = Depends(get_db)
):
    """Verify signup OTP (phone + code) → activate account and log in."""
    tokens = verify_signup_otp(db, data.phone, data.otp)
    if not tokens:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    from app.core.otp_sender import normalize_phone
    user = db.query(User).filter(User.phone == normalize_phone(data.phone)).first()
    if user:
        refresh_days = settings.refresh_token_expire_days_short
        expires_at = datetime.utcnow() + timedelta(days=refresh_days)
        token_hash = _hash_token(tokens.refresh_token)
        db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        db.commit()
    set_token_cookies(response, tokens)
    return tokens

# 🔥 FIXED REGISTER (no password; OTP sent to phone; verify via verify-signup-otp)
@router.post("/register", response_model=dict, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """FR-AUTH-004: Signup (phone required, email optional) → OTP sent → verify-signup-otp"""
    result = register_user(db, data)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(
            status_code=409,
            detail={
                "email_taken": "This email is already registered",
                "phone_taken": "This phone number is already registered"
            }.get(result["error"], "Registration failed")
        )
    
    return result  # {"message": "...", "user_id": XX}

@router.get("/me", response_model=dict)
def me(current_user=Depends(get_current_user)):
    """Current user info"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "phone": current_user.phone,
        "profile_picture": current_user.profile_picture,
        "is_active": current_user.is_active,
        "plan": getattr(current_user, "plan", "trial"),
        "trial_expires_at": current_user.trial_expires_at.isoformat() if getattr(current_user, "trial_expires_at") else None,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat(),
    }
