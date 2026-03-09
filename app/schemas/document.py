"""Document schemas. FR-DOC-001, FR-DOC-003."""
from datetime import datetime

from pydantic import BaseModel, Field


DOC_TAGS = ["Contract", "Blueprint", "RFI", "Inspection Report", "Change Order", "Invoice", "Other"]


class DocumentResponse(BaseModel):
    id: int
    project_id: int | None
    task_id: int | None
    original_filename: str
    file_path: str
    file_size_kb: float
    version: int
    tag: str | None
    uploaded_by: int
    upload_date: datetime

    class Config:
        from_attributes = True


class DocumentVersionResponse(BaseModel):
    id: int
    version: int
    upload_date: datetime
    original_filename: str
