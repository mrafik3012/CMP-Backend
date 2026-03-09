"""Report schemas. Report Templates Requirements 3.2."""
from datetime import date, datetime, time

from pydantic import BaseModel, Field


class ReportWorkforceBase(BaseModel):
    trade: str = Field(..., max_length=50)
    present: int = Field(0, ge=0)
    absent: int = Field(0, ge=0)
    total: int = Field(0, ge=0)


class ReportWorkforceCreate(ReportWorkforceBase):
    pass


class ReportWorkforceResponse(ReportWorkforceBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class ReportWorkItemBase(BaseModel):
    task_name: str = Field(..., max_length=255)
    location: str | None = Field(None, max_length=100)
    boq_item: str | None = Field(None, max_length=50)
    progress_today: float = Field(0, ge=0, le=100)
    progress_cumulative: float = Field(0, ge=0, le=100)


class ReportWorkItemCreate(ReportWorkItemBase):
    pass


class ReportWorkItemResponse(ReportWorkItemBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class ReportMaterialBase(BaseModel):
    item_name: str = Field(..., max_length=255)
    quantity: str | None = Field(None, max_length=50)
    supplier: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=50)


class ReportMaterialCreate(ReportMaterialBase):
    pass


class ReportMaterialResponse(ReportMaterialBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class ReportIssueBase(BaseModel):
    issue_type: str | None = Field(None, max_length=50)
    description: str = Field(..., max_length=2000)
    impact: str | None = Field(None, max_length=20)
    responsible_party: str | None = Field(None, max_length=100)
    status: str = Field("open", max_length=50)


class ReportIssueCreate(ReportIssueBase):
    pass


class ReportIssueResponse(ReportIssueBase):
    id: int
    report_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReportPhotoResponse(BaseModel):
    id: int
    report_id: int
    photo_url: str
    caption: str | None
    latitude: float | None
    longitude: float | None
    taken_at: datetime

    class Config:
        from_attributes = True


class ReportBase(BaseModel):
    report_date: date
    weather: str | None = None
    temperature: float | None = None
    shift_start: str | None = None  # "HH:MM" string for API
    shift_end: str | None = None
    notes: str | None = None


class ReportCreate(ReportBase):
    report_type: str = Field("daily", pattern="^(daily|weekly|monthly)$")
    workforce: list[ReportWorkforceCreate] = Field(default_factory=list)
    work_items: list[ReportWorkItemCreate] = Field(default_factory=list)
    materials: list[ReportMaterialCreate] = Field(default_factory=list)
    issues: list[ReportIssueCreate] = Field(default_factory=list)


class ReportUpdate(BaseModel):
    weather: str | None = None
    temperature: float | None = None
    shift_start: str | None = None
    shift_end: str | None = None
    notes: str | None = None
    status: str | None = None
    workforce: list[ReportWorkforceCreate] | None = None
    work_items: list[ReportWorkItemCreate] | None = None
    materials: list[ReportMaterialCreate] | None = None
    issues: list[ReportIssueCreate] | None = None


class ReportResponse(ReportBase):
    id: int
    report_type: str
    project_id: int
    submitted_by: int
    submitted_at: datetime
    status: str
    is_locked: bool
    workforce: list[ReportWorkforceResponse] = []
    work_items: list[ReportWorkItemResponse] = []
    materials: list[ReportMaterialResponse] = []
    issues: list[ReportIssueResponse] = []
    photos: list[ReportPhotoResponse] = []

    class Config:
        from_attributes = True
