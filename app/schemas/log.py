"""Daily log schemas. FR-LOG-001."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class DailyLogBase(BaseModel):
    date: date
    weather: str = Field(..., pattern="^(Clear|Cloudy|Rain|Snow|Extreme Heat)$")
    workers_present: list[int] | None = None  # worker IDs
    work_completed: str = Field(..., max_length=2000)
    issues: str | None = Field(None, max_length=1000)


class DailyLogCreate(DailyLogBase):
    pass


class DailyLogUpdate(BaseModel):
    weather: str | None = None
    workers_present: list[int] | None = None
    work_completed: str | None = None
    issues: str | None = None


class LogPhotoResponse(BaseModel):
    id: int
    file_path: str
    caption: str | None

    class Config:
        from_attributes = True


class DailyLogResponse(DailyLogBase):
    id: int
    project_id: int
    submitted_by: int
    created_at: datetime

    class Config:
        from_attributes = True
