#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added members listing and PDF report export
"""Project API. Section 6.4. FR-PROJ-001 to FR-PROJ-006."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_db, CurrentUser, RequireAdmin, RequirePMOrAdmin
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectMemberCreate,
    ProjectDashboardStats,
)
from app.services import project_service as svc
from app.db.models import ProjectMember, User
from app.utils.pdf import render_project_summary_pdf

router = APIRouter(prefix="/projects", tags=["projects"])


def _can_edit_project(current_user: CurrentUser, project) -> bool:
    if current_user.role == "Admin":
        return True
    if current_user.role == "Project Manager" and project.created_by == current_user.id:
        return True
    return False


@router.get("", response_model=list[ProjectResponse])
def project_list(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    client: str | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    """List projects (filtered by role in service if needed)."""
    projects = svc.list_projects(db, skip=skip, limit=limit, status=status, client=client, include_archived=include_archived, current_user_id=current_user.id, current_user_role=current_user.role)
    return projects


@router.post("", response_model=ProjectResponse)
def project_create(
    data: ProjectCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    """Create project. PM or Admin."""
    return svc.create_project(db, data, current_user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
def project_get(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/dashboard", response_model=ProjectDashboardStats)
def project_dashboard(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return svc.get_dashboard_stats(db, project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
def project_update(
    project_id: int,
    data: ProjectUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_edit_project(current_user, project):
        raise HTTPException(status_code=403, detail="Cannot edit this project")
    return svc.update_project(db, project, data)


@router.delete("/{project_id}")
def project_delete(
    project_id: int,
    current_user: RequireAdmin,
    db: Session = Depends(get_db),
):
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    svc.soft_delete_project(db, project)
    return {"message": "Project deleted"}


@router.post("/{project_id}/members")
def project_add_member(
    project_id: int,
    data: ProjectMemberCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_edit_project(current_user, project):
        raise HTTPException(status_code=403, detail="Cannot edit this project")
    svc.add_member(db, project_id, data)
    return {"message": "Member added"}


@router.delete("/{project_id}/members/{user_id}")
def project_remove_member(
    project_id: int,
    user_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_edit_project(current_user, project):
        raise HTTPException(status_code=403, detail="Cannot edit this project")
    if not svc.remove_member(db, project_id, user_id):
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member removed"}


@router.get("/{project_id}/members")
def project_members(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """List members of a project."""
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = (
        db.query(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )
    return [
        {
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "role_in_project": pm.role_in_project,
        }
        for pm, u in rows
    ]


@router.get("/{project_id}/report/pdf")
def project_report_pdf(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Generate a simple project summary PDF using weasyprint (placeholder)."""
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = {
        "name": project.name,
        "client": project.client_name,
        "location": project.location,
        "start_date": str(project.start_date),
        "end_date": str(project.end_date),
        "estimated_budget": float(project.estimated_budget or 0),
        "status": project.status,
    }

    from app.core.plan_limits import can_feature
    if not can_feature(current_user, "can_export_pdf"):
        raise HTTPException(
            status_code=403,
            detail="PDF export is not available on the free trial. Please upgrade your plan.",
        )
    pdf_bytes = render_project_summary_pdf(project.name, content)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}-report.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
