"""User service. FR-AUTH-003. NFR-MAINT-003. Auth is mobile OTP only; no password."""
import secrets
from sqlalchemy.orm import Session

from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


def create_user(db: Session, data: UserCreate) -> User:
    """Create user. password_hash set to random (auth is OTP only)."""
    user = User(
        name=data.name,
        email=data.email,
        password_hash=get_password_hash(secrets.token_urlsafe(24)),
        role=data.role,
        phone=data.phone,
        profile_picture=data.profile_picture,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def list_users(db: Session, skip: int = 0, limit: int = 20, active_only: bool = True) -> list[User]:
    q = db.query(User)
    if active_only:
        q = q.filter(User.is_active == True)
    return q.offset(skip).limit(limit).all()


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.phone is not None:
        user.phone = data.phone
    if data.profile_picture is not None:
        user.profile_picture = data.profile_picture
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, user: User) -> User:
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
