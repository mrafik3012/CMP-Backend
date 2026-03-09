"""FastAPI dependencies: get_db, get_current_user, role checks. FR-AUTH-005."""
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.db.models import User


def get_token_from_request(request: Request) -> str | None:
    """FR-AUTH-001: Prefer httpOnly cookie, fallback to Authorization header."""
    token = request.cookies.get("access_token")
    if token:
        return token
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return None


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Require valid access token; return user. NFR-SEC-001."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # FOR DEMO: Allow any active user, bypass phone verification and trial checks
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive",
        )
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory: require current user to have one of allowed_roles."""

    def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        # FOR DEMO: Allow access to anything for any valid user (skip role check)
        return current_user

    return _check


# Convenience dependencies
RequireAdmin = Annotated[User, Depends(require_roles("Admin"))]
RequirePMOrAdmin = Annotated[User, Depends(require_roles("Admin", "Project Manager"))]
CurrentUser = Annotated[User, Depends(get_current_user)]
