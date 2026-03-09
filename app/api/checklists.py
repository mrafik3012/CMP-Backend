"""Inspection Checklists API."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_current_user, get_db
from app.db.models import Checklist, ChecklistItem

router = APIRouter(tags=["checklists"])

# ── Preset templates ──────────────────────────────────────────────────────────
TEMPLATES = {
    "pre-pour": [
        "Reinforcement bars correctly placed and tied",
        "Cover blocks in position",
        "Formwork properly aligned and secured",
        "No debris or water inside formwork",
        "Dowel bars / starter bars in position",
        "Embedments and inserts checked",
        "Ready mix concrete order confirmed",
        "Vibrator available and operational",
        "Supervisor present on site",
    ],
    "safety": [
        "All workers wearing PPE (helmet, vest, boots)",
        "Safety signage displayed",
        "First aid kit available",
        "Fire extinguisher accessible",
        "Scaffolding inspected and certified",
        "Electrical connections properly insulated",
        "Excavation edges barricaded",
        "Emergency contact numbers posted",
        "Housekeeping — walkways clear",
    ],
    "handover": [
        "All snag items resolved",
        "Electrical fittings tested",
        "Plumbing tested — no leaks",
        "Doors and windows operate correctly",
        "Floor finishes complete",
        "Painting complete",
        "Site cleaned and debris removed",
        "As-built drawings handed over",
        "Warranty documents compiled",
        "Client walkthrough completed",
    ],
}


class ChecklistCreate(BaseModel):
    title: str
    checklist_type: str  # pre-pour, safety, handover, custom
    custom_items: Optional[List[str]] = None  # for custom type


class ChecklistItemUpdate(BaseModel):
    is_checked: Optional[bool] = None
    notes: Optional[str] = None


def _serialize_checklist(c: Checklist) -> dict:
    total = len(c.items)
    checked = sum(1 for i in c.items if i.is_checked)
    return {
        "id": c.id,
        "project_id": c.project_id,
        "title": c.title,
        "checklist_type": c.checklist_type,
        "status": c.status,
        "created_by": c.created_by,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
        "total_items": total,
        "checked_items": checked,
        "progress_pct": round(checked / total * 100) if total else 0,
        "items": [
            {
                "id": i.id,
                "item_text": i.item_text,
                "is_checked": i.is_checked,
                "checked_by": i.checked_by,
                "checked_at": i.checked_at.isoformat() if i.checked_at else None,
                "notes": i.notes,
                "sort_order": i.sort_order,
            }
            for i in sorted(c.items, key=lambda x: x.sort_order)
        ],
    }


@router.get("/projects/{project_id}/checklists")
def list_checklists(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    checklists = db.query(Checklist).filter(
        Checklist.project_id == project_id
    ).order_by(Checklist.created_at.desc()).all()
    return [_serialize_checklist(c) for c in checklists]


@router.post("/projects/{project_id}/checklists", status_code=201)
def create_checklist(
    project_id: int,
    data: ChecklistCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    checklist = Checklist(
        project_id=project_id,
        title=data.title,
        checklist_type=data.checklist_type,
        created_by=current_user.id,
    )
    db.add(checklist)
    db.flush()

    # Load template items or custom items
    items_text = TEMPLATES.get(data.checklist_type, data.custom_items or [])
    for idx, text in enumerate(items_text):
        db.add(ChecklistItem(
            checklist_id=checklist.id,
            item_text=text,
            sort_order=idx,
        ))

    db.commit()
    db.refresh(checklist)
    return _serialize_checklist(checklist)


@router.patch("/projects/{project_id}/checklists/{checklist_id}/items/{item_id}")
def update_checklist_item(
    project_id: int,
    checklist_id: int,
    item_id: int,
    data: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if data.is_checked is not None:
        item.is_checked = data.is_checked
        item.checked_by = current_user.id if data.is_checked else None
        item.checked_at = datetime.utcnow() if data.is_checked else None
    if data.notes is not None:
        item.notes = data.notes

    # Auto-update checklist status
    checklist = db.query(Checklist).filter(Checklist.id == checklist_id).first()
    if checklist:
        all_items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist_id).all()
        checked_count = sum(1 for i in all_items if i.is_checked)
        if checked_count == 0:
            checklist.status = "Pending"
        elif checked_count == len(all_items):
            checklist.status = "Completed"
        else:
            checklist.status = "In Progress"

    db.commit()
    db.refresh(item)
    return {"id": item.id, "is_checked": item.is_checked, "notes": item.notes, "checked_at": item.checked_at.isoformat() if item.checked_at else None}


@router.delete("/projects/{project_id}/checklists/{checklist_id}")
def delete_checklist(
    project_id: int,
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    checklist = db.query(Checklist).filter(
        Checklist.id == checklist_id,
        Checklist.project_id == project_id,
    ).first()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    db.delete(checklist)
    db.commit()
    return {"message": "Deleted"}
