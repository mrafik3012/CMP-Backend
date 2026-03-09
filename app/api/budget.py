#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added change-order PATCH and budget CSV export
"""Budget and change order API. Section 6.5, 6.6."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, CurrentUser, RequireAdmin, RequirePMOrAdmin
from app.db.models import BudgetItem, ChangeOrder
from app.schemas.budget import (
    BudgetItemCreate,
    BudgetItemUpdate,
    BudgetItemResponse,
    ChangeOrderCreate,
    ChangeOrderResponse,
    BudgetSummaryChart,
)
from app.services import project_service as psvc
from app.utils.pdf import render_budget_export_pdf

router = APIRouter(tags=["budget"])


@router.get("/projects/{project_id}/budget", response_model=list[BudgetItemResponse])
def budget_list(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    items = db.query(BudgetItem).filter(BudgetItem.project_id == project_id).all()
    return [
        BudgetItemResponse(
            id=x.id,
            project_id=x.project_id,
            category=x.category,
            description=x.description,
            estimated_cost=x.estimated_cost,
            actual_cost=x.actual_cost,
            variance=x.actual_cost - x.estimated_cost,
            created_at=x.created_at,
            updated_at=x.updated_at,
        )
        for x in items
    ]


@router.post("/projects/{project_id}/budget", response_model=BudgetItemResponse)
def budget_create(
    project_id: int,
    data: BudgetItemCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    item = BudgetItem(
        project_id=project_id,
        category=data.category,
        description=data.description,
        estimated_cost=data.estimated_cost,
        actual_cost=data.actual_cost,
        gst_rate=getattr(data, 'gst_rate', 0.0),
        gst_amount=round(getattr(data, 'estimated_cost', 0) * getattr(data, 'gst_rate', 0.0) / 100, 2),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return BudgetItemResponse(
        id=item.id,
        project_id=item.project_id,
        category=item.category,
        description=item.description,
        estimated_cost=item.estimated_cost,
        actual_cost=item.actual_cost,
        variance=item.actual_cost - item.estimated_cost,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put("/budget/{item_id}", response_model=BudgetItemResponse)
def budget_update(
    item_id: int,
    data: BudgetItemUpdate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    item = db.query(BudgetItem).filter(BudgetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return BudgetItemResponse(
        id=item.id,
        project_id=item.project_id,
        category=item.category,
        description=item.description,
        estimated_cost=item.estimated_cost,
        actual_cost=item.actual_cost,
        variance=item.actual_cost - item.estimated_cost,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/budget/{item_id}")
def budget_delete(
    item_id: int,
    current_user: RequireAdmin,
    db: Session = Depends(get_db),
):
    item = db.query(BudgetItem).filter(BudgetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}


@router.get("/projects/{project_id}/budget/summary", response_model=BudgetSummaryChart)
def budget_summary(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    items = db.query(BudgetItem).filter(BudgetItem.project_id == project_id).all()
    return BudgetSummaryChart(
        categories=[x.category for x in items],
        estimated=[x.estimated_cost for x in items],
        actual=[x.actual_cost for x in items],
        variance=[x.actual_cost - x.estimated_cost for x in items],
    )


@router.get("/projects/{project_id}/change-orders", response_model=list[ChangeOrderResponse])
def change_order_list(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(ChangeOrder).filter(ChangeOrder.project_id == project_id).all()


@router.post("/projects/{project_id}/change-orders", response_model=ChangeOrderResponse)
def change_order_create(
    project_id: int,
    data: ChangeOrderCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    from sqlalchemy import func
    n = db.query(func.max(ChangeOrder.change_order_number)).filter(ChangeOrder.project_id == project_id).scalar() or 0
    co = ChangeOrder(
        project_id=project_id,
        change_order_number=n + 1,
        description=data.description,
        cost_impact=data.cost_impact,
        justification=data.justification,
        requested_by=current_user.id,
        status="Pending",
    )
    db.add(co)
    db.commit()
    db.refresh(co)
    return co


@router.put("/change-orders/{co_id}/approve", response_model=ChangeOrderResponse)
def change_order_approve(
    co_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    from datetime import datetime
    co = db.query(ChangeOrder).filter(ChangeOrder.id == co_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Change order not found")
    co.status = "Approved"
    co.approved_by = current_user.id
    co.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(co)
    return co


@router.put("/change-orders/{co_id}/reject", response_model=ChangeOrderResponse)
def change_order_reject(
    co_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    co = db.query(ChangeOrder).filter(ChangeOrder.id == co_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Change order not found")
    co.status = "Rejected"
    db.commit()
    db.refresh(co)
    return co


class ChangeOrderStatusUpdate(BaseModel):
    status: str


@router.patch("/change-orders/{co_id}", response_model=ChangeOrderResponse)
def change_order_update_status(
    co_id: int,
    data: ChangeOrderStatusUpdate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    """Update change order status (approve/reject) via PATCH."""
    from datetime import datetime

    co = db.query(ChangeOrder).filter(ChangeOrder.id == co_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Change order not found")
    if data.status not in {"Approved", "Rejected"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    co.status = data.status
    if data.status == "Approved":
        co.approved_by = current_user.id
        co.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(co)
    return co


@router.get("/projects/{project_id}/budget/export/csv")
def budget_export_csv(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Export project budget items to CSV. Same access as viewing the budget list."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    items = (
        db.query(BudgetItem)
        .filter(BudgetItem.project_id == project_id)
        .order_by(BudgetItem.category)
        .all()
    )
    headers = [
        "id",
        "project_id",
        "category",
        "description",
        "estimated_cost",
        "actual_cost",
        "variance",
    ]
    lines = [",".join(headers)]
    for x in items:
        variance = x.actual_cost - x.estimated_cost
        safe_category = (x.category or "").replace('"', '""')
        safe_description = (x.description or "").replace('"', '""')
        row = [
            str(x.id),
            str(x.project_id),
            f'"{safe_category}"',
            f'"{safe_description}"',
            str(x.estimated_cost),
            str(x.actual_cost),
            str(variance),
        ]
        lines.append(",".join(row))
    csv_data = "\n".join(lines)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}-budget.csv"'
        },
    )


@router.get("/projects/{project_id}/budget/export/pdf")
def budget_export_pdf(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Export project budget as formatted PDF (brand, table layout). Same access as budget list."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    items = (
        db.query(BudgetItem)
        .filter(BudgetItem.project_id == project_id)
        .order_by(BudgetItem.category)
        .all()
    )
    project = psvc.get_project(db, project_id)
    project_name = project.name if project else f"Project {project_id}"
    payload = [
        {
            "category": x.category,
            "description": x.description,
            "estimated_cost": float(x.estimated_cost or 0),
            "actual_cost": float(x.actual_cost or 0),
        }
        for x in items
    ]
    pdf_bytes = render_budget_export_pdf(project_name, payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}-budget.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
