"""Task service. FR-TASK-005, FR-TASK-006, FR-TASK-007. NFR-MAINT-003."""
import json
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Task, Notification
from app.schemas.task import TaskCreate, TaskUpdate


def _deps_to_json(deps: list[int] | None) -> str | None:
    if not deps:
        return None
    return json.dumps(deps)


def _json_to_deps(s: str | None) -> list[int]:
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []


def create_task(db: Session, project_id: int, data: TaskCreate, user_id: int) -> Task:
    task = Task(
        project_id=project_id,
        parent_task_id=data.parent_task_id,
        title=data.title,
        description=data.description,
        assignee_id=data.assignee_id,
        start_date=data.start_date,
        due_date=data.due_date,
        priority=data.priority,
        status=data.status,
        dependencies=_deps_to_json(data.dependencies),
        estimated_hours=data.estimated_hours,
        actual_hours=data.actual_hours,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if data.assignee_id:
        _notify_task_assigned(db, data.assignee_id, task.id, project_id)
    return task


def _notify_task_assigned(db: Session, assignee_id: int, task_id: int, project_id: int) -> None:
    n = Notification(
        user_id=assignee_id,
        message="A task has been assigned to you.",
        link=f"/projects/{project_id}/tasks?task={task_id}",
    )
    db.add(n)
    db.commit()


def get_task(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def update_task(db: Session, task: Task, data: TaskUpdate) -> Task:
    if data.assignee_id is not None and task.assignee_id != data.assignee_id:
        _notify_task_assigned(db, data.assignee_id, task.project_id, task.id)
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "dependencies":
            setattr(task, k, _deps_to_json(v))
        else:
            setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return task


def update_task_status(db: Session, task: Task, status: str) -> Task:
    if status == "Done":
        deps = _json_to_deps(task.dependencies)
        for dep_id in deps:
            dep = db.query(Task).filter(Task.id == dep_id).first()
            if dep and dep.status != "Done":
                raise ValueError("Cannot mark Done: dependencies incomplete")
    task.status = status
    db.commit()
    db.refresh(task)
    return task


def assign_task(db: Session, task: Task, assignee_id: int) -> Task:
    task.assignee_id = assignee_id
    db.commit()
    db.refresh(task)
    _notify_task_assigned(db, assignee_id, task.id, task.project_id)
    return task
