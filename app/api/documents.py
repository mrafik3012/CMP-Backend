#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added project document upload/list/download/delete API
"""Documents API."""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, CurrentUser, RequirePMOrAdmin
from app.db.models import Document
from app.schemas.document import DocumentResponse
from app.utils.image import compress_to_webp
from app.services import project_service as psvc

router = APIRouter(prefix="/projects", tags=["documents"])

UPLOAD_ROOT = Path("uploads")


@router.get("/{project_id}/documents", response_model=list[DocumentResponse])
def document_list(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  if not psvc.get_project(db, project_id):
      raise HTTPException(status_code=404, detail="Project not found")
  docs = (
      db.query(Document)
      .filter(Document.project_id == project_id)
      .order_by(Document.upload_date.desc())
      .all()
  )
  return docs


@router.post("/{project_id}/documents", response_model=DocumentResponse)
async def document_upload(
    project_id: int,
    current_user: RequirePMOrAdmin,        # â† Depends() args first
    db: Session = Depends(get_db),
    file: UploadFile = File(...),          # â† File/Form args after
    tag: Annotated[str | None, Form()] = None,
):
  if not psvc.get_project(db, project_id):
      raise HTTPException(status_code=404, detail="Project not found")

  project_dir = UPLOAD_ROOT / str(project_id)
  project_dir.mkdir(parents=True, exist_ok=True)

  original_name = file.filename or "upload"
  raw_path = project_dir / original_name
  content = await file.read()
  raw_path.write_bytes(content)

  suffix = raw_path.suffix.lower()
  final_path = raw_path
  data_bytes = content

  if suffix in {".jpg", ".jpeg", ".png"}:
      webp_bytes = compress_to_webp(raw_path)
      final_path = project_dir / (raw_path.stem + ".webp")
      final_path.write_bytes(webp_bytes)
      data_bytes = webp_bytes

  size_kb = len(data_bytes) / 1024

  version = (
      db.query(Document)
      .filter(Document.project_id == project_id, Document.original_filename == original_name)
      .count()
      + 1
  )

  doc = Document(
      project_id=project_id,
      task_id=None,
      original_filename=original_name,
      file_path=str(final_path),
      file_size_kb=size_kb,
      version=version,
      tag=tag,
      uploaded_by=current_user.id,
  )
  db.add(doc)
  db.commit()
  db.refresh(doc)
  return doc


@router.get("/documents/{document_id}/download")
def document_download(
    document_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  doc = db.query(Document).filter(Document.id == document_id).first()
  if not doc:
      raise HTTPException(status_code=404, detail="Document not found")
  path = Path(doc.file_path)
  if not path.is_file():
      raise HTTPException(status_code=404, detail="File not found")
  return FileResponse(
      path=str(path),
      filename=doc.original_filename,
  )


@router.delete("/documents/{document_id}")
def document_delete(
    document_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  doc = db.query(Document).filter(Document.id == document_id).first()
  if not doc:
      raise HTTPException(status_code=404, detail="Document not found")
  path = Path(doc.file_path)
  if path.is_file():
      try:
          path.unlink()
      except OSError:
          pass
  db.delete(doc)
  db.commit()
  return {"message": "Deleted"}

