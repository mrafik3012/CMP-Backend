"""Budget and change order schemas. FR-BUDGET-001, FR-BUDGET-002."""
from datetime import date, datetime
from pydantic import BaseModel, Field

BUDGET_CATEGORIES = ["Labour", "Materials", "Equipment", "Subcontractor", "Overheads", "Contingency"]


class BudgetItemBase(BaseModel):
    category: str = Field(..., pattern="^(Labour|Materials|Equipment|Subcontractor|Overheads|Contingency)$")
    description: str | None = Field(None, max_length=500)
    estimated_cost: float = Field(..., ge=0)
    actual_cost: float = Field(0, ge=0)
    gst_rate: float = Field(0.0, ge=0, le=28)
    gst_amount: float = Field(0.0, ge=0)


class BudgetItemCreate(BudgetItemBase):
    pass


class BudgetItemUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    estimated_cost: float | None = Field(None, ge=0)
    actual_cost: float | None = Field(None, ge=0)
    gst_rate: float | None = Field(None, ge=0, le=28)
    gst_amount: float | None = Field(None, ge=0)


class BudgetItemResponse(BudgetItemBase):
    id: int
    project_id: int
    variance: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChangeOrderCreate(BaseModel):
    description: str = Field(..., max_length=1000)
    cost_impact: float
    justification: str


class ChangeOrderResponse(BaseModel):
    id: int
    project_id: int
    change_order_number: int
    description: str
    cost_impact: float
    justification: str
    requested_by: int
    approved_by: int | None
    status: str
    created_at: datetime
    approved_at: datetime | None

    class Config:
        from_attributes = True


class BudgetSummaryChart(BaseModel):
    categories: list[str]
    estimated: list[float]
    actual: list[float]
    variance: list[float]
