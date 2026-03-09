#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added daily site logs API with PDF export
"""Daily site logs API."""
import json
from datetime import date as date_type
from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, CurrentUser, RequirePMOrAdmin
from app.db.models import DailyLog, LogPhoto
from app.schemas.log import (
    DailyLogCreate,
    DailyLogUpdate,
    DailyLogResponse,
    LogPhotoResponse,
)
from app.services import project_service as psvc
from app.utils.pdf import render_log_pdf

router = APIRouter(prefix="/projects", tags=["logs"])

LOG_UPLOAD_ROOT = Path("uploads/logs")


@router.get("/{project_id}/logs", response_model=list[DailyLogResponse])
def log_list(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  if not psvc.get_project(db, project_id):
      raise HTTPException(status_code=404, detail="Project not found")
  logs = (
      db.query(DailyLog)
      .filter(DailyLog.project_id == project_id)
      .order_by(DailyLog.date.desc())
      .all()
  )
  for l in logs:
      # deserialize workers_present JSON if stored
      if l.workers_present:
          try:
              l.workers_present = json.loads(l.workers_present)
          except Exception:
              pass
  return logs


@router.post("/{project_id}/logs", response_model=DailyLogResponse)
async def log_create(
    project_id: int,
    data: DailyLogCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  if not psvc.get_project(db, project_id):
      raise HTTPException(status_code=404, detail="Project not found")
  existing = (
      db.query(DailyLog)
      .filter(DailyLog.project_id == project_id, DailyLog.date == data.date)
      .first()
  )
  if existing:
      raise HTTPException(status_code=400, detail="Log for this date already exists")
  workers_json = json.dumps(data.workers_present or [])
  log = DailyLog(
      project_id=project_id,
      date=data.date,
      weather=data.weather,
      workers_present=workers_json,
      work_completed=data.work_completed,
      issues=data.issues,
      submitted_by=current_user.id,
  )
  db.add(log)
  db.commit()
  db.refresh(log)
  # Deserialize workers_present for response model (expects list, not JSON string)
  if log.workers_present:
      try:
          log.workers_present = json.loads(log.workers_present)
      except Exception:
          log.workers_present = []
  return log


@router.get("/{project_id}/logs/{log_date}", response_model=DailyLogResponse)
def log_get_by_date(
    project_id: int,
    log_date: date_type,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  log = (
      db.query(DailyLog)
      .filter(DailyLog.project_id == project_id, DailyLog.date == log_date)
      .first()
  )
  if not log:
      raise HTTPException(status_code=404, detail="Log not found")
  if log.workers_present:
      try:
          log.workers_present = json.loads(log.workers_present)
      except Exception:
          pass
  return log


@router.put("/logs/{log_id}", response_model=DailyLogResponse)
def log_update(
    log_id: int,
    data: DailyLogUpdate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  log = db.query(DailyLog).filter(DailyLog.id == log_id).first()
  if not log:
      raise HTTPException(status_code=404, detail="Log not found")
  if data.weather is not None:
      log.weather = data.weather
  if data.workers_present is not None:
      log.workers_present = json.dumps(data.workers_present)
  if data.work_completed is not None:
      log.work_completed = data.work_completed
  if data.issues is not None:
      log.issues = data.issues
  db.commit()
  db.refresh(log)
  return log


@router.post("/logs/{log_id}/photos", response_model=LogPhotoResponse)
async def log_add_photo(
    log_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
  log = db.query(DailyLog).filter(DailyLog.id == log_id).first()
  if not log:
      raise HTTPException(status_code=404, detail="Log not found")
  log_dir = LOG_UPLOAD_ROOT / str(log_id)
  log_dir.mkdir(parents=True, exist_ok=True)
  content = await file.read()
  path = log_dir / (file.filename or "photo.jpg")
  path.write_bytes(content)
  photo = LogPhoto(log_id=log_id, file_path=str(path), caption=None)
  db.add(photo)
  db.commit()
  db.refresh(photo)
  return photo


@router.get("/logs/{log_id}/export/pdf")
def log_export_pdf(
    log_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  log = db.query(DailyLog).filter(DailyLog.id == log_id).first()
  if not log:
      raise HTTPException(status_code=404, detail="Log not found")
  if log.workers_present:
      try:
          workers = json.loads(log.workers_present)
      except Exception:
          workers = []
  else:
      workers = []
  content = {
      "date": str(log.date),
      "weather": log.weather,
      "workers_present": workers,
      "work_completed": log.work_completed,
      "issues": log.issues,
  }
  pdf_bytes = render_log_pdf(str(log.project_id), str(log.date), content)
  tmp_dir = Path(tempfile.gettempdir())
  file_path = tmp_dir / f"log-{log_id}.pdf"
  file_path.write_bytes(pdf_bytes)
  return FileResponse(
      path=str(file_path),
      media_type="application/pdf",
      filename=f"log-{log_id}.pdf",
  )


@router.post("/{project_id}/logs/{log_date}/photos")
def upload_log_photo(
    project_id: int,
    log_date: str,
    file: UploadFile = File(...),
    caption: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a photo to a daily log entry. log_date must be YYYY-MM-DD."""
    from app.db.models import DailyLog, LogPhoto
    import shutil, uuid, os
    from app.core.config import get_settings
    from datetime import datetime as dt
    settings = get_settings()
    backend_root = Path(__file__).resolve().parent.parent.parent
    base_upload = (backend_root / settings.upload_dir).resolve()

    try:
        parsed_date = dt.strptime(log_date, "%Y-%m-%d").date() if isinstance(log_date, str) else log_date
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid log_date; use YYYY-MM-DD")

    log = db.query(DailyLog).filter(
        DailyLog.project_id == project_id,
        DailyLog.date == parsed_date,
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found for this date")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")

    upload_dir = os.path.join(str(base_upload), "log_photos", str(log.id))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f_out:
        shutil.copyfileobj(file.file, f_out)

    photo = LogPhoto(
        log_id=log.id,
        file_path=f"/uploads/log_photos/{log.id}/{filename}",
        caption=caption or None,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return {"id": photo.id, "file_path": photo.file_path, "caption": photo.caption}


@router.get("/{project_id}/logs/{log_date}/photos")
def get_log_photos(
    project_id: int,
    log_date: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all photos for a daily log. log_date must be YYYY-MM-DD."""
    from app.db.models import DailyLog, LogPhoto
    from datetime import datetime as dt
    try:
        parsed_date = dt.strptime(log_date, "%Y-%m-%d").date() if isinstance(log_date, str) else log_date
    except (ValueError, TypeError):
        return []
    log = db.query(DailyLog).filter(
        DailyLog.project_id == project_id,
        DailyLog.date == parsed_date,
    ).first()
    if not log:
        return []
    photos = db.query(LogPhoto).filter(LogPhoto.log_id == log.id).all()
    return [{"id": p.id, "file_path": p.file_path, "caption": p.caption, "uploaded_at": p.uploaded_at.isoformat()} for p in photos]


@router.delete("/{project_id}/logs/{log_date}/photos/{photo_id}")
def delete_log_photo(
    project_id: int,
    log_date: str,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a log photo. log_date must be YYYY-MM-DD."""
    from app.db.models import LogPhoto
    from datetime import datetime as dt
    import os
    photo = db.query(LogPhoto).filter(LogPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Delete file from disk
    disk_path = os.path.join(r"F:\Cursor-demo\backend", photo.file_path.lstrip("/").replace("/", os.sep))
    if os.path.exists(disk_path):
        os.remove(disk_path)
    db.delete(photo)
    db.commit()
    return {"message": "Deleted"}
