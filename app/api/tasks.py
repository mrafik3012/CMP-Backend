#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added PATCH update and CSV export for tasks
"""Task API. Section 6.5."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import Response

from app.core.deps import get_db, CurrentUser, RequirePMOrAdmin
from app.db.models import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskAssignRequest, GanttTaskItem
from app.services import project_service as psvc
from app.services import task_service as tsvc
from app.utils.pdf import render_tasks_export_pdf

router = APIRouter(tags=["tasks"])


def _task_to_response(task: Task) -> TaskResponse:
    deps = []
    if task.dependencies:
        try:
            deps = json.loads(task.dependencies)
        except Exception:
            pass
    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        parent_task_id=task.parent_task_id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee_id,
        start_date=task.start_date,
        due_date=task.due_date,
        priority=task.priority,
        status=task.status,
        dependencies=deps,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours,
        is_critical_path=task.is_critical_path,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def task_list(
    project_id: int,
  current_user: CurrentUser,
  db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.due_date).all()
    return [_task_to_response(t) for t in tasks]


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse)
def task_create(
    project_id: int,
    data: TaskCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    project = psvc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    task = tsvc.create_task(db, project_id, data, current_user.id)
    return _task_to_response(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def task_get(
    task_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    task = tsvc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def task_update(
    task_id: int,
    data: TaskUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    task = tsvc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        task = tsvc.update_task(db, task, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _task_to_response(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def task_partial_update(
    task_id: int,
    data: TaskUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Partial update for a task (PATCH semantics)."""
    task = tsvc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        task = tsvc.update_task(db, task, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _task_to_response(task)


@router.delete("/tasks/{task_id}")
def task_delete(
    task_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    task = tsvc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


@router.get("/projects/{project_id}/gantt", response_model=list[GanttTaskItem])
def gantt_data(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    result = []
    for t in tasks:
        try:
            deps = json.loads(t.dependencies) if t.dependencies else []
        except Exception:
            deps = []
        result.append(
            GanttTaskItem(
                id=t.id,
                title=t.title,
                start_date=t.start_date,
                end_date=t.due_date,
                status=t.status,
                is_critical_path=t.is_critical_path,
                dependencies=deps,
            )
        )
    return result


@router.post("/tasks/{task_id}/assign", response_model=TaskResponse)
def task_assign(
    task_id: int,
    data: TaskAssignRequest,
  current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    task = tsvc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tsvc.assign_task(db, task, data.assignee_id)
    return _task_to_response(task)


@router.get("/tasks/export/csv")
def tasks_export_csv(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Export all tasks to CSV for reporting."""
    tasks = db.query(Task).order_by(Task.project_id, Task.due_date).all()
    headers = [
        "id",
        "project_id",
        "title",
        "assignee_id",
        "start_date",
        "due_date",
        "priority",
        "status",
    ]
    lines = [",".join(headers)]
    for t in tasks:
        safe_title = (t.title or "").replace('"', '""')
        row = [
            str(t.id),
            str(t.project_id),
            f'"{safe_title}"',
            "" if t.assignee_id is None else str(t.assignee_id),
            t.start_date.isoformat() if t.start_date else "",
            t.due_date.isoformat() if t.due_date else "",
            t.priority or "",
            t.status or "",
        ]
        lines.append(",".join(row))
    csv_data = "\n".join(lines)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tasks.csv"'},
    )


@router.get("/projects/{project_id}/tasks/export/csv")
def project_tasks_export_csv(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Export tasks for a specific project to CSV."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.due_date)
        .all()
    )
    headers = [
        "id",
        "project_id",
        "title",
        "assignee_id",
        "start_date",
        "due_date",
        "priority",
        "status",
    ]
    lines = [",".join(headers)]
    for t in tasks:
        safe_title = (t.title or "").replace('"', '""')
        row = [
            str(t.id),
            str(t.project_id),
            f'"{safe_title}"',
            "" if t.assignee_id is None else str(t.assignee_id),
            t.start_date.isoformat() if t.start_date else "",
            t.due_date.isoformat() if t.due_date else "",
            t.priority or "",
            t.status or "",
        ]
        lines.append(",".join(row))
    csv_data = "\n".join(lines)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}-tasks.csv"'
        },
    )


@router.get("/projects/{project_id}/tasks/export/pdf")
def project_tasks_export_pdf(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Export project tasks as formatted PDF (brand, table layout). Same access as task list."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.due_date)
        .all()
    )
    project = psvc.get_project(db, project_id)
    project_name = project.name if project else f"Project {project_id}"
    payload = [
        {
            "title": t.title,
            "start_date": t.start_date.isoformat() if t.start_date else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "priority": t.priority,
            "status": t.status,
            "estimated_hours": t.estimated_hours,
            "actual_hours": t.actual_hours,
        }
        for t in tasks
    ]
    pdf_bytes = render_tasks_export_pdf(project_name, payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}-tasks.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )

