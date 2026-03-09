# update_user_verification.py
"""
Add OTP verification fields to existing User model and migrate data.
Run ONCE after adding columns to DB schema.
"""

from sqlalchemy import inspect, create_engine
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine  # engine now imported
from app.db.models.user import User

def add_verification_columns():
    """Check if columns exist."""
    inspector = inspect(engine)  # Use engine directly
    existing = [col['name'] for col in inspector.get_columns('users')]
    
    missing = []
    required = ['is_email_verified', 'is_phone_verified', 'email_otp_hash', 
                'phone_otp_hash', 'otp_expires_at']
    
    for col in required:
        if col not in existing:
            missing.append(col)
    
    if missing:
        print(f"⚠️  MISSING COLUMNS: {missing}")
        print("1. Add to app/db/models/user.py:")
        print("   is_email_verified = Column(Boolean, default=False)")
        print("   # ... other 4 columns")
        print("2. alembic revision --autogenerate -m 'add otp fields'")
        print("3. alembic upgrade head")
        sys.exit(1)
    print("✅ All OTP columns exist")

def migrate_existing_users():
    """Set existing users to verified."""
    db = SessionLocal()
    users = db.query(User).all()
    updated = 0
    
    for user in users:
        changed = False
        if not getattr(user, 'is_email_verified', False) and user.email:
            user.is_email_verified = True
            changed = True
        if not getattr(user, 'is_phone_verified', False) and user.phone:
            user.is_phone_verified = True
            changed = True
        
        if changed:
            updated += 1
    
    db.commit()
    db.close()
    print(f"✅ Grandfathered {updated}/{len(users)} users")

def test_login():
    """Auth is mobile OTP only; no password login."""
    print("ℹ️  Auth is mobile OTP only; skip password login check")
    return True

def main():
    print("🔄 Infraura OTP Verification Migration")
    print("=" * 50)
    
    add_verification_columns()
    migrate_existing_users()
    test_login()
    
    print("\n🎉 Migration complete!")
    print("New users: Signup → Email OTP + SMS OTP → Active")
    print("Existing users: Already verified ✅")

if __name__ == "__main__":
    main()