"""Worker, equipment, task resource schemas. FR-RESOURCE-001, FR-RESOURCE-002."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class WorkerBase(BaseModel):
    name: str
    trade: str
    hourly_rate: float = Field(0, ge=0)
    phone: str | None = None
    email: str | None = None
    availability: str = Field(..., pattern="^(Available|Assigned|On Leave)$")


class WorkerCreate(WorkerBase):
    pass


class WorkerResponse(WorkerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EquipmentBase(BaseModel):
    name: str
    type: str
    daily_cost: float = Field(0, ge=0)
    status: str = Field(..., pattern="^(Available|Assigned|Under Maintenance)$")


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentResponse(EquipmentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskResourceAssign(BaseModel):
    resource_id: int
    resource_type: str = Field(..., pattern="^(worker|equipment)$")
    start_date: date
    end_date: date
