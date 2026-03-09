#!/usr/bin/env python
# MODIFIED: 2026-03-04 - Registered all routers including punch_list, checklists, audit_log
from fastapi import APIRouter


from app.api import (
    auth, users, projects, tasks, budget, notifications,
    dashboard, resources, documents, logs, rfis,
    audit_log, punch_list, checklists, reports
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(budget.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(resources.router)
api_router.include_router(documents.router)
api_router.include_router(logs.router)
api_router.include_router(rfis.router)
api_router.include_router(audit_log.router)
api_router.include_router(punch_list.router)
api_router.include_router(checklists.router)
api_router.include_router(reports.router)
