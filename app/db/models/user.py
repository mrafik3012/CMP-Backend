"""User model with plan/trial fields."""
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('contractor','homeowner','architect','subcontractor','project_manager','consultant','Admin','Project Manager','Site Engineer','Viewer')",
            name="ck_users_role_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    profile_picture: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="trial"
    )
    trial_started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    trial_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    storage_used_mb: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # OTP VERIFICATION FIELDS (SPACE INDENTATION):
    is_email_verified: Mapped[bool | None] = mapped_column(
        Boolean, default=False, nullable=True
    )
    is_phone_verified: Mapped[bool | None] = mapped_column(
        Boolean, default=False, nullable=True
    )
    email_otp_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_otp_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )