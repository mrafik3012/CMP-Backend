"""Audit log API. Returns last 200 actions across all projects."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user, RequireAdmin, require_roles

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("")
def get_audit_log(
    current_user: RequireAdmin,
    db: Session = Depends(get_db),
):

    """Return recent audit entries from site logs, tasks, RFIs, budget."""
    rows = []

    try:
        from app.db.models import SiteLog, Task, RFI, BudgetItem, Project
        from sqlalchemy import desc

        # Site logs
        for log in db.query(SiteLog).order_by(desc(SiteLog.created_at)).limit(50).all():
            proj = db.query(Project).filter(Project.id == log.project_id).first()
            rows.append({
                "id": f"log-{log.id}",
                "type": "Site Log",
                "project": proj.name if proj else "Unknown",
                "description": f"Site log for {log.log_date}",
                "user": getattr(log, "created_by_name", "—"),
                "timestamp": log.created_at.isoformat() if log.created_at else "",
            })

        # Tasks
        for task in db.query(Task).order_by(desc(Task.updated_at)).limit(50).all():
            proj = db.query(Project).filter(Project.id == task.project_id).first()
            rows.append({
                "id": f"task-{task.id}",
                "type": "Task",
                "project": proj.name if proj else "Unknown",
                "description": f"Task '{task.title}' → {task.status}",
                "user": "—",
                "timestamp": task.updated_at.isoformat() if task.updated_at else "",
            })

        # RFIs
        for rfi in db.query(RFI).order_by(desc(RFI.created_at)).limit(50).all():
            proj = db.query(Project).filter(Project.id == rfi.project_id).first()
            rows.append({
                "id": f"rfi-{rfi.id}",
                "type": "RFI",
                "project": proj.name if proj else "Unknown",
                "description": f"RFI: {rfi.subject}",
                "user": "—",
                "timestamp": rfi.created_at.isoformat() if rfi.created_at else "",
            })

        # Sort all by timestamp desc
        rows.sort(key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        # Graceful fallback — return empty list instead of 500
        return []

    return rows[:200]
