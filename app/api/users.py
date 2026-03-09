#!/usr/bin/env python
"""User API. Section 6.3. FR-AUTH-003."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, RequireAdmin, CurrentUser, get_current_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.db.models import User
from app.services.user_service import (
    create_user,
    get_user_by_id,
    get_user_by_email,
    list_users,
    update_user,
    soft_delete_user,
)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserListResponse])
def user_list(
    current_user: RequireAdmin,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all users (paginated). Admin only."""
    users = list_users(db, skip=skip, limit=limit)
    return users


@router.post("", response_model=UserResponse)
def user_create(
    data: UserCreate,
    current_user: RequireAdmin,
    db: Session = Depends(get_db),
):
    """Create user. Auth is mobile OTP only (no password). Admin only."""
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(db, data)
    return user


@router.get("/export/csv")
def export_users_csv(
    current_user: RequireAdmin,
    db: Session = Depends(get_db),
):
    """Admin only: export all users as CSV."""
    import csv, io
    from fastapi.responses import StreamingResponse
    all_users = db.query(User).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Phone", "Role", "Status", "Created At"])
    for u in all_users:
        writer.writerow([
            u.id, u.name, u.email,
            u.phone or "",
            u.role,
            "Active" if u.is_active else "Inactive",
            u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )


@router.get("/{user_id}", response_model=UserResponse)
def user_get(
    user_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get user by ID. Any authenticated user."""
    if current_user.role != "Admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def user_update(
    user_id: int,
    data: UserUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Update user. Admin or self."""
    if current_user.role != "Admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return update_user(db, user, data)


@router.delete("/{user_id}")
def user_delete(
    user_id: int,
    current_user: RequireAdmin,
    db: Session = Depends(get_db),
):
    """Soft delete user. Admin only."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    soft_delete_user(db, user)
    return {"message": "User deactivated"}


