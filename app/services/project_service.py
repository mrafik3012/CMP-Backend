"""Project service. FR-PROJ-001 to FR-PROJ-006. NFR-MAINT-003."""
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Project, ProjectMember, Task
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate


def create_project(db: Session, data: ProjectCreate, created_by: int) -> Project:
    project = Project(
        name=data.name,
        client_name=data.client_name,
        location=data.location,
        start_date=data.start_date,
        end_date=data.end_date,
        estimated_budget=data.estimated_budget,
        sqft=data.sqft,
        project_type=data.project_type,
        project_category=data.project_category,
        status=data.status,
        description=data.description,
        created_by=created_by,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: int, include_deleted: bool = False) -> Project | None:
    q = db.query(Project).filter(Project.id == project_id)
    if not include_deleted:
        q = q.filter(Project.is_deleted == False)
    return q.first()


def list_projects(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    client: str | None = None,
    include_archived: bool = False,
    current_user_id: int | None = None,
    current_user_role: str | None = None,
) -> list[Project]:
    q = db.query(Project).filter(Project.is_deleted == False)
    if not include_archived:
        q = q.filter(Project.archived == False)
    if status:
        q = q.filter(Project.status == status)
    if client:
        q = q.filter(Project.client_name.ilike(f"%{client}%"))

    # Non-admin users only see projects they created or are a member of
    if current_user_role and current_user_role != "Admin":
        member_project_ids = db.query(ProjectMember.project_id).filter(
            ProjectMember.user_id == current_user_id
        ).subquery()
        q = q.filter(
            (Project.created_by == current_user_id) |
            (Project.id.in_(member_project_ids))
        )

    q = q.order_by(Project.updated_at.desc()).offset(skip).limit(limit)
    return q.all()


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


def soft_delete_project(db: Session, project: Project) -> Project:
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def add_member(db: Session, project_id: int, data: ProjectMemberCreate) -> ProjectMember:
    pm = ProjectMember(project_id=project_id, user_id=data.user_id, role_in_project=data.role_in_project)
    db.add(pm)
    db.commit()
    db.refresh(pm)
    return pm


def remove_member(db: Session, project_id: int, user_id: int) -> bool:
    deleted = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).delete()
    db.commit()
    return deleted > 0


def get_dashboard_stats(db: Session, project_id: int) -> dict[str, Any]:
    """FR-PROJ-003: progress %, budget burn %, overdue count, last updated."""
    from datetime import date
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {}
    total = db.query(func.count(Task.id)).filter(Task.project_id == project_id).scalar() or 0
    done = (
        db.query(func.count(Task.id))
        .filter(Task.project_id == project_id, Task.status == "Done")
        .scalar()
        or 0
    )
    progress = (done / total * 100) if total else 0
    from app.db.models import BudgetItem
    budget_rows = db.query(BudgetItem).filter(BudgetItem.project_id == project_id).all()
    actual_spend = sum(r.actual_cost for r in budget_rows)
    budget_burn = (actual_spend / project.estimated_budget * 100) if project.estimated_budget else 0
    overdue = (
        db.query(func.count(Task.id))
        .filter(
            Task.project_id == project_id,
            Task.due_date < date.today(),
            Task.status != "Done",
        )
        .scalar()
        or 0
    )
    return {
        "progress_percent": round(progress, 1),
        "budget_burn_percent": round(budget_burn, 1),
        "overdue_tasks_count": overdue,
        "last_updated": project.updated_at,
    }
