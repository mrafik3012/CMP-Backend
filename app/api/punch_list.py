"""Punch list / snag list API."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_current_user, get_db
from app.db.models import PunchItem

router = APIRouter(tags=["punch-list"])


class PunchItemCreate(BaseModel):
    title: str
    location: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    priority: str = "Medium"
    due_date: Optional[str] = None


class PunchItemUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None


def _serialize(p: PunchItem) -> dict:
    return {
        "id": p.id,
        "project_id": p.project_id,
        "title": p.title,
        "location": p.location,
        "description": p.description,
        "assigned_to": p.assigned_to,
        "status": p.status,
        "priority": p.priority,
        "due_date": str(p.due_date) if p.due_date else None,
        "photo_path": p.photo_path,
        "created_by": p.created_by,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


@router.get("/projects/{project_id}/punch-list")
def list_punch_items(
    project_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(PunchItem).filter(PunchItem.project_id == project_id)
    if status:
        q = q.filter(PunchItem.status == status)
    if priority:
        q = q.filter(PunchItem.priority == priority)
    return [_serialize(p) for p in q.order_by(PunchItem.created_at.desc()).all()]


@router.post("/projects/{project_id}/punch-list", status_code=201)
def create_punch_item(
    project_id: int,
    data: PunchItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = PunchItem(
        project_id=project_id,
        title=data.title,
        location=data.location,
        description=data.description,
        assigned_to=data.assigned_to,
        priority=data.priority,
        due_date=date.fromisoformat(data.due_date) if data.due_date else None,
        created_by=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.patch("/projects/{project_id}/punch-list/{item_id}")
def update_punch_item(
    project_id: int,
    item_id: int,
    data: PunchItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(PunchItem).filter(
        PunchItem.id == item_id,
        PunchItem.project_id == project_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Punch item not found")
    for field, value in data.model_dump(exclude_none=True).items():
        if field == "due_date" and value:
            setattr(item, field, date.fromisoformat(value))
        else:
            setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.delete("/projects/{project_id}/punch-list/{item_id}")
def delete_punch_item(
    project_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(PunchItem).filter(
        PunchItem.id == item_id,
        PunchItem.project_id == project_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Punch item not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}


@router.post("/projects/{project_id}/punch-list/{item_id}/photo")
def upload_punch_photo(
    project_id: int,
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    import shutil, uuid, os
    item = db.query(PunchItem).filter(
        PunchItem.id == item_id,
        PunchItem.project_id == project_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Punch item not found")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")

    upload_dir = os.path.join("uploads", "punch_photos", str(item_id))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f_out:
        shutil.copyfileobj(file.file, f_out)

    item.photo_path = f"/uploads/punch_photos/{item_id}/{filename}"
    db.commit()
    return {"photo_path": item.photo_path}
