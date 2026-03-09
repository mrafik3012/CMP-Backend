#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added RFI CRUD API
"""RFI API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, CurrentUser, RequirePMOrAdmin
from app.db.models import RFI
from app.schemas.rfi import RFICreate, RFIUpdate, RFIResponse
from app.services import project_service as psvc

router = APIRouter(prefix="/projects", tags=["rfis"])


@router.get("/{project_id}/rfis", response_model=list[RFIResponse])
def rfi_list(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  if not psvc.get_project(db, project_id):
      raise HTTPException(status_code=404, detail="Project not found")
  rfis = (
      db.query(RFI)
      .filter(RFI.project_id == project_id)
      .order_by(RFI.due_date.asc())
      .all()
  )
  return rfis


@router.post("/{project_id}/rfis", response_model=RFIResponse)
def rfi_create(
    project_id: int,
    data: RFICreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  if not psvc.get_project(db, project_id):
      raise HTTPException(status_code=404, detail="Project not found")
  rfi = RFI(
      project_id=project_id,
      title=data.title,
      description=data.description,
      raised_by=current_user.id,
      assigned_to=data.assigned_to,
      due_date=data.due_date,
      status="Open",
  )
  db.add(rfi)
  db.commit()
  db.refresh(rfi)
  return rfi


@router.get("/rfis/{rfi_id}", response_model=RFIResponse)
def rfi_get(
    rfi_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  rfi = db.query(RFI).filter(RFI.id == rfi_id).first()
  if not rfi:
      raise HTTPException(status_code=404, detail="RFI not found")
  return rfi


@router.put("/rfis/{rfi_id}", response_model=RFIResponse)
def rfi_update(
    rfi_id: int,
    data: RFIUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  rfi = db.query(RFI).filter(RFI.id == rfi_id).first()
  if not rfi:
      raise HTTPException(status_code=404, detail="RFI not found")
  if current_user.role not in {"Admin", "Project Manager"} and current_user.id != rfi.assigned_to:
      raise HTTPException(status_code=403, detail="Forbidden")
  for k, v in data.model_dump(exclude_unset=True).items():
      setattr(rfi, k, v)
  db.commit()
  db.refresh(rfi)
  return rfi


@router.delete("/rfis/{rfi_id}")
def rfi_delete(
    rfi_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  rfi = db.query(RFI).filter(RFI.id == rfi_id).first()
  if not rfi:
      raise HTTPException(status_code=404, detail="RFI not found")
  db.delete(rfi)
  db.commit()
  return {"message": "Deleted"}

