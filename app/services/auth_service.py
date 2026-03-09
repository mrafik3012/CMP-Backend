"""Auth service. FR-AUTH-001 to FR-AUTH-004. NFR-MAINT-003. Mobile OTP login."""
import random
import secrets
from datetime import datetime, timedelta
from typing import Any

# TOP of auth_service.py
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.otp_sender import normalize_phone, send_login_otp
from app.core.security import (
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.models import User
from app.schemas.auth import RegisterRequest, TokenResponse

settings = get_settings()

# Test users (for bypass and for OTP lookup when phone not set in DB)
TEST_USER_EMAILS = frozenset({
    "admin@example.com",
    "pm@infraura.com",
    "engineer@infraura.com",
    "viewer@infraura.com",
})
# Test phone -> email so we can find test users even if phone was never set (e.g. old DB)
TEST_PHONE_TO_EMAIL = {
    "+919876543201": "admin@example.com",
    "+919876543202": "pm@infraura.com",
    "+919876543203": "engineer@infraura.com",
    "+919876543204": "viewer@infraura.com",
}


def create_tokens_for_user(user: User, remember_me: bool | None = None) -> TokenResponse:
    extra = {"role": user.role}
    access = create_access_token(user.id, extra=extra)
    refresh = create_refresh_token(user.id, remember_me=remember_me)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse | None:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        return None
    extra = {"role": user.role}
    access = create_access_token(user.id, extra=extra)
    remember_me_flag = payload.get("remember_me")
    new_refresh = create_refresh_token(user.id, remember_me=remember_me_flag)
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def send_login_otp_to_user(db: Session, phone: str) -> dict:
    """Look up user by PHONE only (email is never used for lookup).
    Send OTP via SMS to phone; if user has email we also send there as optional backup.
    Returns {message} or {error}."""
    import logging
    log = logging.getLogger(__name__)
    raw = (phone or "").strip()
    normalized = normalize_phone(raw)
    log.info("send_login_otp: raw=%r normalized=%r", raw, normalized)
    print(f"[OTP] send_login_otp: raw={raw!r} normalized={normalized!r}")  # always visible in terminal

    user = db.query(User).filter(User.phone == normalized).first()
    if user:
        log.info("send_login_otp: user found by phone (id=%s)", user.id)
        print(f"[OTP] user found by phone id={user.id}")
    # Fallback: match if phone stored without leading + (e.g. 919876543201)
    if not user and normalized.startswith("+"):
        user = db.query(User).filter(User.phone == normalized[1:]).first()
        if user:
            user.phone = normalized
            db.commit()
            log.info("send_login_otp: user found by phone without + (id=%s)", user.id)
            print(f"[OTP] user found by phone (no +) id={user.id}")
    # Fallback for test users: find by known test phone -> email (case-insensitive)
    if not user and normalized in TEST_PHONE_TO_EMAIL:
        email = TEST_PHONE_TO_EMAIL[normalized]
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.phone = normalized
            user.is_phone_verified = True
            db.commit()
            log.info("send_login_otp: user found by test email (id=%s email=%s)", user.id, user.email)
            print(f"[OTP] user found by test email id={user.id} email={user.email}")
    if not user:
        log.warning("send_login_otp: no user for normalized=%r", normalized)
        print(f"[OTP] no user found for normalized={normalized!r}")
        return {"error": "phone_not_found"}
    if not user.is_active:
        return {"error": "account_disabled"}
    otp = str(random.randint(100000, 999999))
    user.phone_otp_hash = pwd_context.hash(otp)
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    send_login_otp(normalized, otp, user.email)
    return {"message": "OTP sent to your phone"}


def verify_login_otp_and_get_user(
    db: Session, phone: str, otp: str, remember_me: bool
) -> TokenResponse | None:
    """Verify OTP and return tokens. Clears OTP from user. E2E: when e2e_otp_bypass set, accept that OTP for test phones."""
    normalized = normalize_phone(phone)
    bypass = (settings.e2e_otp_bypass or "").strip()
    if bypass and otp == bypass and normalized in TEST_PHONE_TO_EMAIL:
        user = db.query(User).filter(User.phone == normalized).first()
        if not user:
            user = db.query(User).filter(User.phone == normalized[1:]).first()
        if not user:
            user = db.query(User).filter(User.email == TEST_PHONE_TO_EMAIL[normalized]).first()
            if user:
                user.phone = normalized
                db.commit()
        if user and user.is_active:
            return create_tokens_for_user(user, remember_me=remember_me)

    user = db.query(User).filter(User.phone == normalized).first()
    if not user and normalized.startswith("+"):
        user = db.query(User).filter(User.phone == normalized[1:]).first()
        if user:
            user.phone = normalized
            db.commit()
    if not user:
        return None
    if not user.phone_otp_hash or not user.otp_expires_at:
        return None
    if datetime.utcnow() > user.otp_expires_at:
        return None
    if not pwd_context.verify(otp, user.phone_otp_hash):
        return None
    user.phone_otp_hash = None
    user.otp_expires_at = None
    db.commit()
    return create_tokens_for_user(user, remember_me=remember_me)


def register_user(db: Session, data: RegisterRequest) -> dict:
    """Signup: phone mandatory, email optional. No password; auth via OTP."""
    normalized_phone = normalize_phone(data.phone)
    if db.query(User).filter(User.phone == normalized_phone).first():
        return {"error": "phone_taken"}
    if data.email and db.query(User).filter(User.email == data.email).first():
        return {"error": "email_taken"}

    user_count = db.query(User).count()
    role = "Admin" if user_count == 0 else data.role
    trial_days = settings.trial_expire_days
    # OTP-only users: store a random password hash so column stays NOT NULL
    random_password = secrets.token_urlsafe(24)
    user = User(
        name=data.name,
        email=data.email or None,
        phone=normalized_phone,
        password_hash=get_password_hash(random_password),
        role=role,
        is_active=False,
        is_email_verified=False,
        is_phone_verified=False,
        plan="trial",
        trial_started_at=datetime.utcnow(),
        trial_expires_at=datetime.utcnow() + timedelta(days=trial_days),
        storage_used_mb=0.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    phone_otp = str(random.randint(100000, 999999))
    user.phone_otp_hash = pwd_context.hash(phone_otp)
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    from app.core.otp_sender import send_otp_sms, send_otp_email
    send_otp_sms(normalized_phone, phone_otp)
    if user.email:
        send_otp_email(user.email, phone_otp)

    print(f"🔐 NEW USER #{user.id} (phone {normalized_phone})")
    print(f"   Phone OTP: {phone_otp}")
    return {"message": "OTP sent to your phone. Verify to activate.", "user_id": user.id}


def verify_signup_otp(db: Session, phone: str, otp: str) -> TokenResponse | None:
    """Verify signup OTP by phone → activate user and return tokens."""
    normalized = normalize_phone(phone)
    user = db.query(User).filter(
        User.phone == normalized,
        User.is_active == False,
        User.phone_otp_hash.is_not(None),
    ).first()
    if not user or not user.otp_expires_at or datetime.utcnow() > user.otp_expires_at:
        return None
    if not pwd_context.verify(otp, user.phone_otp_hash):
        return None
    user.phone_otp_hash = None
    user.otp_expires_at = None
    user.is_phone_verified = True
    user.is_active = True
    user.is_email_verified = True  # treat phone verification as sufficient for signup
    db.commit()
    return create_tokens_for_user(user, remember_me=False)