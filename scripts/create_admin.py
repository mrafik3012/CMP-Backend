"""Create initial seed users.

Run:
  python -m scripts.create_admin

Creates (if missing) and updates (if existing) test users with emails and phone numbers.
Auth is mobile OTP only (no password). Re-run to set phone on existing users.

- admin@example.com      +919876543201  (Admin)
- pm@infraura.com        +919876543202  (Project Manager)
- engineer@infraura.com  +919876543203  (Site Engineer)
- viewer@infraura.com    +919876543204  (Viewer)
"""
import os
import secrets
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal, init_db
from app.db.models import User
from app.core.security import get_password_hash
from app.core.otp_sender import normalize_phone

# (email, name, role, phone)
TEST_USERS = [
    ("admin@example.com", "Admin", "Admin", "+919876543201"),
    ("pm@infraura.com", "Project Manager", "Project Manager", "+919876543202"),
    ("engineer@infraura.com", "Site Engineer", "Site Engineer", "+919876543203"),
    ("viewer@infraura.com", "Viewer", "Viewer", "+919876543204"),
]


def ensure_user(db, *, name: str, email: str, role: str, phone: str) -> None:
    """Create or update a test user. Auth is mobile OTP only (no password)."""
    normalized_phone = normalize_phone(phone)
    user = db.query(User).filter(User.email == email).first()
    placeholder_hash = get_password_hash(secrets.token_urlsafe(24))
    if user:
        user.name = name
        user.role = role
        user.password_hash = placeholder_hash
        user.phone = normalized_phone
        user.is_active = True
        if hasattr(user, "is_email_verified"):
            user.is_email_verified = True
        if hasattr(user, "is_phone_verified"):
            user.is_phone_verified = True
        db.commit()
        print(f"Updated existing user {email} (phone {normalized_phone}) to role={role}.")
        return

    user = User(
        name=name,
        email=email,
        phone=normalized_phone,
        password_hash=placeholder_hash,
        role=role,
        is_active=True,
    )
    if hasattr(user, "is_email_verified"):
        user.is_email_verified = True
    if hasattr(user, "is_phone_verified"):
        user.is_phone_verified = True

    db.add(user)
    db.commit()
    print(f"Created {email} / phone {normalized_phone} ({role})")


def main():
    init_db()
    db = SessionLocal()
    # Use same DB as the app: run from backend/ so database_url resolves correctly
    from app.core.config import get_settings
    print("DB:", get_settings().database_url)

    # Backfill phone for existing test users that have no phone
    for email, name, role, phone in TEST_USERS:
        user = db.query(User).filter(User.email == email).first()
        if user and (not user.phone or not user.phone.strip()):
            user.phone = normalize_phone(phone)
            user.is_phone_verified = True
            user.is_active = True
            db.commit()
            print(f"Backfilled phone for {email} -> {user.phone}")

    for email, name, role, phone in TEST_USERS:
        ensure_user(db, name=name, email=email, role=role, phone=phone)

    db.close()

if __name__ == "__main__":
    main()
