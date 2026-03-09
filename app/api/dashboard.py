#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added recent activity endpoint
"""Dashboard API. Section 6.13. FR-REPORT-003."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, CurrentUser
from app.db.models import Project, Task, BudgetItem, AuditLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard_overview(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Active projects count, overdue tasks, budget committed vs spent, upcoming deadlines."""
    active_projects = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False,
        Project.status == "Active",
    ).scalar() or 0
    overdue = db.query(func.count(Task.id)).filter(
        Task.due_date < date.today(),
        Task.status != "Done",
    ).scalar() or 0
    projects = db.query(Project).filter(Project.is_deleted == False).all()
    total_budget = sum(p.estimated_budget for p in projects)
    total_actual = 0
    for p in projects:
        total_actual += db.query(func.coalesce(func.sum(BudgetItem.actual_cost), 0)).filter(
            BudgetItem.project_id == p.id
        ).scalar() or 0
    end = date.today() + timedelta(days=7)
    upcoming = db.query(Task).filter(
        Task.due_date >= date.today(),
        Task.due_date <= end,
        Task.status != "Done",
    ).order_by(Task.due_date).limit(10).all()
    return {
        "active_projects_count": active_projects,
        "overdue_tasks_count": overdue,
        "total_budget_committed": total_budget,
        "total_actual_spent": total_actual,
        "upcoming_deadlines": [
            {"id": t.id, "title": t.title, "due_date": str(t.due_date), "project_id": t.project_id}
            for t in upcoming
        ],
    }


@router.get("/activity")
def dashboard_activity(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Recent 10 audit log entries for activity feed."""
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": log.id,
            "action": log.action,
            "entity": log.table_name,
            "created_at": log.timestamp,
            "type": log.action,
        }
        for log in logs
    ]
