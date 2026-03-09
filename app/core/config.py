"""Environment and app configuration. NFR-MAINT-001."""
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache

# Backend package root (app/core/config.py -> app/core -> app -> backend)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB_PATH = _BACKEND_ROOT / "app.db"


class Settings(BaseSettings):
    """App settings from environment."""

    database_url: str = f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}"

    @field_validator("database_url", mode="before")
    @classmethod
    def resolve_db_url(cls, v: str) -> str:
        """Resolve relative SQLite paths OR fix Render's postgres:// prefix."""
        if not isinstance(v, str):
            return v
            
        # Fix Render postgres:// prefix
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
            
        # Resolve SQLite path
        if v.startswith("sqlite:///") and "./" in v:
            rest = v.replace("sqlite:///", "").lstrip("./").replace("\\", "/")
            if rest and not rest.startswith("/"):
                abs_path = (_BACKEND_ROOT / rest).resolve()
                return f"sqlite:///{abs_path.as_posix()}"
        return v
    secret_key: str = "your-secret-key-min-32-chars-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # Default refresh lifetime (used when Remember Me flag is not specified)
    refresh_token_expire_days: int = 7
    # Remember Me behaviour: 1-day default vs 7-day extended session
    refresh_token_expire_days_short: int = 1
    refresh_token_expire_days_long: int = 7
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 25
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Free trial duration (days). Default 90 = 3 months.
    trial_expire_days: int = 90
    # E2E only: fixed OTP that works for test phones when set (e.g. 123456). No email/password.
    e2e_otp_bypass: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
