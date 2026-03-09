"""Project schemas. FR-PROJ-001."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ProjectType = Literal["Residential", "Commercial", "Industrial", "Infrastructure"]
ProjectCategory = Literal[
    "Construction",
    "Interior",
    "Renovation",
    "Smart Automation",
    "Roofing",
    "PEB",
]


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=200)
    client_name: str
    location: str
    start_date: date
    end_date: date
    estimated_budget: float = Field(..., ge=0)
    sqft: int = Field(..., ge=1, le=999_999)
    project_type: ProjectType
    project_category: ProjectCategory
    status: str = Field(
        ...,
        pattern="^(Planning|Active|On Hold|Completed|Cancelled)$",
    )
    description: str | None = Field(None, max_length=5000)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    client_name: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    estimated_budget: float | None = Field(None, ge=0)
    sqft: int | None = Field(None, ge=1, le=999_999)
    project_type: ProjectType | None = None
    project_category: ProjectCategory | None = None
    status: str | None = Field(None, pattern="^(Planning|Active|On Hold|Completed|Cancelled)$")
    description: str | None = None
    archived: bool | None = None


class ProjectMemberCreate(BaseModel):
    user_id: int
    role_in_project: str = Field(
        ...,
        pattern="^(Project Manager|Site Engineer|Viewer)$",
    )


class ProjectResponse(ProjectBase):
    id: int
    archived: bool
    is_deleted: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDashboardStats(BaseModel):
    progress_percent: float
    budget_burn_percent: float
    overdue_tasks_count: int
    last_updated: datetime
