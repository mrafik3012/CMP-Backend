"""Task schemas. FR-TASK-001, FR-TASK-002."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    assignee_id: int | None = None
    start_date: date
    due_date: date
    priority: str = Field(
        ...,
        pattern="^(Low|Medium|High|Critical)$",
    )
    status: str = Field(
        ...,
        pattern="^(Not Started|In Progress|On Hold|Completed|Blocked|Done)$",
    )
    parent_task_id: int | None = None
    dependencies: list[int] | None = None  # JSON array of task IDs
    estimated_hours: float | None = Field(None, ge=0)
    actual_hours: float | None = Field(None, ge=0)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    assignee_id: int | None = None
    start_date: date | None = None
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None
    parent_task_id: int | None = None
    dependencies: list[int] | None = None
    estimated_hours: float | None = None
    actual_hours: float | None = None


class TaskAssignRequest(BaseModel):
    assignee_id: int


class TaskResponse(TaskBase):
    id: int
    project_id: int
    is_critical_path: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GanttTaskItem(BaseModel):
    id: int
    title: str
    start_date: date
    end_date: date
    status: str
    is_critical_path: bool
    dependencies: list[int] | None = None
