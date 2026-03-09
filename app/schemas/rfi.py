"""RFI and Issue schemas. FR-RFI-001, FR-RFI-004."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class RFIBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=2000)
    assigned_to: int
    due_date: date


class RFICreate(RFIBase):
    pass


class RFIUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: int | None = None
    due_date: date | None = None
    response: str | None = None
    status: str | None = Field(None, pattern="^(Open|Pending Response|Closed)$")


class RFIResponse(RFIBase):
    id: int
    project_id: int
    raised_by: int
    status: str
    response: str | None
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class IssueBase(BaseModel):
    title: str
    description: str
    severity: str = Field(..., pattern="^(Low|Medium|High|Critical)$")
    linked_task_id: int | None = None


class IssueCreate(IssueBase):
    pass


class IssueUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = Field(None, pattern="^(Open|In Progress|Resolved)$")
    resolution_notes: str | None = Field(None, max_length=1000)


class IssueResponse(IssueBase):
    id: int
    project_id: int
    status: str
    resolution_notes: str | None
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True
