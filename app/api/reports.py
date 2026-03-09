"""Reports API. Report Templates Requirements 3.2."""
from datetime import date, time, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user, get_db, CurrentUser, RequirePMOrAdmin
from app.db.models import Report, ReportWorkforce, ReportWorkItem, ReportMaterial, ReportIssue, ReportPhoto, Project, User, Task, Worker
from app.schemas.report import (
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportWorkforceCreate,
    ReportWorkItemResponse,
    ReportWorkforceResponse,
    ReportMaterialResponse,
    ReportIssueResponse,
    ReportPhotoResponse,
    ReportWorkItemCreate,
    ReportMaterialCreate,
    ReportIssueCreate,
)
from app.services import project_service as psvc
from app.utils.pdf import render_daily_report_pdf, render_weekly_report_pdf, render_monthly_report_pdf, render_test_pdf

router = APIRouter(tags=["reports"])

REPORT_UPLOAD_ROOT = Path("uploads/reports")


def _parse_time(s: str | None) -> time | None:
    if not s:
        return None
    try:
        parts = s.strip().split(":")
        if len(parts) >= 2:
            return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        pass
    return None


def _task_status_to_progress_pct(status: str | None) -> float:
    """Map task status to approximate cumulative progress for draft."""
    if not status:
        return 0.0
    s = status.strip().lower()
    if s == "done":
        return 100.0
    if s == "in progress":
        return 50.0
    if s == "blocked":
        return 25.0
    return 0.0  # Not Started or unknown


def _build_draft_payload(db: Session, project_id: int, report_date: date) -> dict:
    """Build daily report payload from existing data (tasks, workers). No DB write."""
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.due_date).all()
    work_items = [
        {
            "task_name": t.title,
            "location": "",
            "boq_item": "",
            "progress_today": 0,
            "progress_cumulative": _task_status_to_progress_pct(t.status),
        }
        for t in tasks
    ]
    if not work_items:
        work_items = [{"task_name": "", "location": "", "boq_item": "", "progress_today": 0, "progress_cumulative": 0}]

    trades_from_workers = [r[0] for r in db.query(Worker.trade).distinct().all() if r[0] and str(r[0]).strip()]
    workforce = [{"trade": t, "present": 0, "absent": 0, "total": 0} for t in trades_from_workers]
    if not workforce:
        workforce = [{"trade": "", "present": 0, "absent": 0, "total": 0}]

    return {
        "report_date": str(report_date),
        "weather": "Clear",
        "temperature": None,
        "shift_start": "08:00",
        "shift_end": "18:00",
        "notes": "",
        "workforce": workforce,
        "work_items": work_items,
        "materials": [{"item_name": "", "quantity": "", "supplier": "", "status": ""}],
        "issues": [{"issue_type": "", "description": "", "impact": "", "responsible_party": ""}],
    }


@router.get("/projects/{project_id}/reports/daily-draft")
def get_daily_report_draft(
    project_id: int,
    current_user: CurrentUser,
    report_date: date | None = None,
    db: Session = Depends(get_db),
):
    """Pre-fill daily report from project data: tasks → work items, workers → workforce trades."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return _build_draft_payload(db, project_id, report_date or date.today())


def _report_to_response(r: Report) -> ReportResponse:
    return ReportResponse(
        id=r.id,
        report_type=r.report_type,
        project_id=r.project_id,
        report_date=r.report_date,
        submitted_by=r.submitted_by,
        submitted_at=r.submitted_at,
        status=r.status,
        weather=r.weather,
        temperature=float(r.temperature) if r.temperature is not None else None,
        shift_start=r.shift_start.strftime("%H:%M") if r.shift_start else None,
        shift_end=r.shift_end.strftime("%H:%M") if r.shift_end else None,
        notes=r.notes,
        is_locked=r.is_locked,
        workforce=[ReportWorkforceResponse.model_validate(w) for w in r.workforce],
        work_items=[ReportWorkItemResponse.model_validate(i) for i in r.work_items],
        materials=[ReportMaterialResponse.model_validate(m) for m in r.materials],
        issues=[ReportIssueResponse.model_validate(i) for i in r.issues],
        photos=[ReportPhotoResponse.model_validate(p) for p in r.photos],
    )


@router.get("/projects/{project_id}/reports/daily/pdf")
def export_daily_report_pdf_on_demand(
    project_id: int,
    current_user: CurrentUser,
    report_date: date | None = None,
    db: Session = Depends(get_db),
):
    """Generate daily report PDF from existing data. No form: select date and download.
    Uses saved report for that date if one exists; otherwise builds from tasks + workers."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    draft_date = report_date or date.today()
    if draft_date > date.today():
        raise HTTPException(status_code=400, detail="Report date cannot be in the future")

    project = psvc.get_project(db, project_id)
    project_name = project.name if project else f"Project {project_id}"

    existing = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
        )
        .filter(
            Report.project_id == project_id,
            Report.report_date == draft_date,
            Report.report_type == "daily",
        )
        .first()
    )

    if existing:
        submitter = db.query(User).filter(User.id == existing.submitted_by).first()
        created_by_name = submitter.name if submitter else None
        payload = {
            "report_date": str(existing.report_date),
            "created_by_name": created_by_name,
            "weather": existing.weather or "",
            "temperature": existing.temperature,
            "shift_start": existing.shift_start.strftime("%H:%M") if existing.shift_start else "",
            "shift_end": existing.shift_end.strftime("%H:%M") if existing.shift_end else "",
            "notes": existing.notes or "",
            "workforce": [{"trade": w.trade, "present": w.present, "absent": w.absent, "total": w.total} for w in existing.workforce],
            "work_items": [
                {
                    "task_name": wi.task_name,
                    "location": wi.location or "",
                    "boq_item": wi.boq_item or "",
                    "progress_today": float(wi.progress_today),
                    "progress_cumulative": float(wi.progress_cumulative),
                }
                for wi in existing.work_items
            ],
            "materials": [{"item_name": m.item_name, "quantity": m.quantity or "", "supplier": m.supplier or "", "status": m.status or ""} for m in existing.materials],
            "issues": [{"issue_type": i.issue_type or "", "description": i.description, "impact": i.impact or "", "responsible_party": i.responsible_party or ""} for i in existing.issues],
        }
    else:
        payload = _build_draft_payload(db, project_id, draft_date)
        payload["created_by_name"] = current_user.name if current_user else None

    pdf_bytes = render_daily_report_pdf(project_name, payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="daily-report-{draft_date}-{project_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.post("/projects/{project_id}/reports/daily", response_model=ReportResponse)
def create_daily_report(
    project_id: int,
    data: ReportCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if data.report_type != "daily":
        data = data.model_copy(update={"report_type": "daily"})
    existing = (
        db.query(Report)
        .filter(
            Report.project_id == project_id,
            Report.report_date == data.report_date,
            Report.report_type == "daily",
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="A daily report for this date already exists")
    if data.report_date > date.today():
        raise HTTPException(status_code=400, detail="Report date cannot be in the future")

    report = Report(
        report_type="daily",
        project_id=project_id,
        report_date=data.report_date,
        submitted_by=current_user.id,
        weather=data.weather,
        temperature=data.temperature,
        shift_start=_parse_time(data.shift_start),
        shift_end=_parse_time(data.shift_end),
        notes=data.notes,
    )
    db.add(report)
    db.flush()
    for w in data.workforce:
        rw = ReportWorkforce(
            report_id=report.id,
            trade=w.trade,
            present=w.present,
            absent=w.absent,
            total=w.total,
        )
        db.add(rw)
    for wi in data.work_items:
        ri = ReportWorkItem(
            report_id=report.id,
            task_name=wi.task_name,
            location=wi.location,
            boq_item=wi.boq_item,
            progress_today=wi.progress_today,
            progress_cumulative=wi.progress_cumulative,
        )
        db.add(ri)
    for m in data.materials:
        rm = ReportMaterial(
            report_id=report.id,
            item_name=m.item_name,
            quantity=m.quantity,
            supplier=m.supplier,
            status=m.status,
        )
        db.add(rm)
    for i in data.issues:
        riss = ReportIssue(
            report_id=report.id,
            issue_type=i.issue_type,
            description=i.description,
            impact=i.impact,
            responsible_party=i.responsible_party,
            status=i.status,
        )
        db.add(riss)
    db.commit()
    db.refresh(report)
    report = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
            selectinload(Report.photos),
        )
        .filter(Report.id == report.id)
        .first()
    )
    return _report_to_response(report)


@router.get("/projects/{project_id}/reports/daily", response_model=list[ReportResponse])
def list_daily_reports(
    project_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    from_date: date | None = None,
    to_date: date | None = None,
):
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    q = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
            selectinload(Report.photos),
        )
        .filter(Report.project_id == project_id, Report.report_type == "daily")
        .order_by(Report.report_date.desc())
    )
    if from_date:
        q = q.filter(Report.report_date >= from_date)
    if to_date:
        q = q.filter(Report.report_date <= to_date)
    reports = q.limit(100).all()
    return [_report_to_response(r) for r in reports]


@router.get("/reports/test-pdf")
def test_pdf():
    """Return a minimal PDF with visible text. No auth required so you can open in browser to verify PDF generation."""
    try:
        pdf_bytes = render_test_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="test-report.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
            selectinload(Report.photos),
        )
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_response(report)


@router.put("/reports/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    data: ReportUpdate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
            selectinload(Report.photos),
        )
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.is_locked:
        raise HTTPException(status_code=400, detail="Report is locked and cannot be edited")

    if data.weather is not None:
        report.weather = data.weather
    if data.temperature is not None:
        report.temperature = data.temperature
    if data.shift_start is not None:
        report.shift_start = _parse_time(data.shift_start)
    if data.shift_end is not None:
        report.shift_end = _parse_time(data.shift_end)
    if data.notes is not None:
        report.notes = data.notes
    if data.status is not None:
        report.status = data.status

    if data.workforce is not None:
        db.query(ReportWorkforce).filter(ReportWorkforce.report_id == report_id).delete()
        for w in data.workforce:
            db.add(
                ReportWorkforce(
                    report_id=report_id,
                    trade=w.trade,
                    present=w.present,
                    absent=w.absent,
                    total=w.total,
                )
            )
    if data.work_items is not None:
        db.query(ReportWorkItem).filter(ReportWorkItem.report_id == report_id).delete()
        for wi in data.work_items:
            db.add(
                ReportWorkItem(
                    report_id=report_id,
                    task_name=wi.task_name,
                    location=wi.location,
                    boq_item=wi.boq_item,
                    progress_today=wi.progress_today,
                    progress_cumulative=wi.progress_cumulative,
                )
            )
    if data.materials is not None:
        db.query(ReportMaterial).filter(ReportMaterial.report_id == report_id).delete()
        for m in data.materials:
            db.add(
                ReportMaterial(
                    report_id=report_id,
                    item_name=m.item_name,
                    quantity=m.quantity,
                    supplier=m.supplier,
                    status=m.status,
                )
            )
    if data.issues is not None:
        db.query(ReportIssue).filter(ReportIssue.report_id == report_id).delete()
        for i in data.issues:
            db.add(
                ReportIssue(
                    report_id=report_id,
                    issue_type=i.issue_type,
                    description=i.description,
                    impact=i.impact,
                    responsible_party=i.responsible_party,
                    status=i.status,
                )
            )
    db.commit()
    db.refresh(report)
    report = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
            selectinload(Report.photos),
        )
        .filter(Report.id == report_id)
        .first()
    )
    return _report_to_response(report)


@router.post("/reports/{report_id}/submit", response_model=ReportResponse)
def submit_report(
    report_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == "submitted":
        return _report_to_response(
            db.query(Report)
            .options(
                selectinload(Report.workforce),
                selectinload(Report.work_items),
                selectinload(Report.materials),
                selectinload(Report.issues),
                selectinload(Report.photos),
            )
            .filter(Report.id == report_id)
            .first()
        )
    report.status = "submitted"
    db.commit()
    db.refresh(report)
    report = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
            selectinload(Report.photos),
        )
        .filter(Report.id == report_id)
        .first()
    )
    return _report_to_response(report)


@router.get("/reports/{report_id}/export/pdf")
def export_report_pdf(
    report_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
            selectinload(Report.photos),
        )
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    project = db.query(Project).filter(Project.id == report.project_id).first()
    project_name = project.name if project else f"Project {report.project_id}"
    submitter = db.query(User).filter(User.id == report.submitted_by).first()
    created_by_name = submitter.name if submitter else None
    payload = {
        "report_date": str(report.report_date),
        "created_by_name": created_by_name,
        "weather": report.weather or "",
        "temperature": report.temperature,
        "shift_start": report.shift_start.strftime("%H:%M") if report.shift_start else "",
        "shift_end": report.shift_end.strftime("%H:%M") if report.shift_end else "",
        "notes": report.notes or "",
        "workforce": [
            {"trade": w.trade, "present": w.present, "absent": w.absent, "total": w.total}
            for w in report.workforce
        ],
        "work_items": [
            {
                "task_name": wi.task_name,
                "location": wi.location or "",
                "boq_item": wi.boq_item or "",
                "progress_today": float(wi.progress_today),
                "progress_cumulative": float(wi.progress_cumulative),
            }
            for wi in report.work_items
        ],
        "materials": [
            {
                "item_name": m.item_name,
                "quantity": m.quantity or "",
                "supplier": m.supplier or "",
                "status": m.status or "",
            }
            for m in report.materials
        ],
        "issues": [
            {
                "issue_type": i.issue_type or "",
                "description": i.description,
                "impact": i.impact or "",
                "responsible_party": i.responsible_party or "",
            }
            for i in report.issues
        ],
    }
    pdf_bytes = render_daily_report_pdf(project_name, payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="daily-report-{report.report_date}-{report_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


def _aggregate_reports_payload(reports: list) -> dict:
    """Build a single payload from multiple daily reports (work_items merged by task_name, workforce summed by trade)."""
    work_by_task: dict[str, dict] = {}
    wf_by_trade: dict[str, dict] = {}
    materials: list = []
    issues: list = []
    for r in reports:
        for wi in r.work_items:
            key = (wi.task_name or "").strip() or "_"
            if key not in work_by_task:
                work_by_task[key] = {
                    "task_name": wi.task_name or "—",
                    "location": wi.location or "",
                    "boq_item": wi.boq_item or "",
                    "progress_today": float(wi.progress_today or 0),
                    "progress_cumulative": float(wi.progress_cumulative or 0),
                }
            else:
                work_by_task[key]["progress_today"] += float(wi.progress_today or 0)
                work_by_task[key]["progress_cumulative"] = max(
                    work_by_task[key]["progress_cumulative"], float(wi.progress_cumulative or 0)
                )
        for w in r.workforce:
            t = (w.trade or "").strip() or "_"
            if t not in wf_by_trade:
                wf_by_trade[t] = {"trade": w.trade or "—", "present": 0, "absent": 0, "total": 0}
            wf_by_trade[t]["present"] += int(w.present or 0)
            wf_by_trade[t]["absent"] += int(w.absent or 0)
            wf_by_trade[t]["total"] += int(w.total or 0)
        for m in r.materials:
            materials.append({
                "item_name": m.item_name or "",
                "quantity": m.quantity or "",
                "supplier": m.supplier or "",
                "status": m.status or "",
            })
        for i in r.issues:
            issues.append({
                "issue_type": i.issue_type or "",
                "description": i.description or "",
                "impact": i.impact or "",
                "responsible_party": i.responsible_party or "",
            })
    return {
        "report_date": str(reports[0].report_date) if reports else "",
        "created_by_name": None,
        "weather": "",
        "temperature": None,
        "shift_start": None,
        "shift_end": None,
        "notes": "",
        "workforce": list(wf_by_trade.values()),
        "work_items": list(work_by_task.values()),
        "materials": materials,
        "issues": issues,
    }


@router.get("/projects/{project_id}/reports/weekly/pdf")
def export_weekly_report_pdf(
    project_id: int,
    week_start: date,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Generate weekly report PDF for the 7-day period starting week_start. No form — data from daily reports in range."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    week_end = week_start + timedelta(days=6)
    reports = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
        )
        .filter(
            Report.project_id == project_id,
            Report.report_type == "daily",
            Report.report_date >= week_start,
            Report.report_date <= week_end,
        )
        .order_by(Report.report_date)
        .all()
    )
    project = db.query(Project).filter(Project.id == project_id).first()
    project_name = project.name if project else f"Project {project_id}"
    period_label = f"{week_start.strftime('%d %b')} – {week_end.strftime('%d %b, %Y')}"
    payload = _aggregate_reports_payload(reports) if reports else {
        "report_date": str(week_start),
        "created_by_name": None,
        "weather": "", "temperature": None, "shift_start": None, "shift_end": None, "notes": "",
        "workforce": [], "work_items": [], "materials": [], "issues": [],
    }
    payload["report_date"] = str(week_start)
    pdf_bytes = render_weekly_report_pdf(project_name, payload, period_label)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="weekly-report-{week_start}-{project_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/projects/{project_id}/reports/monthly/pdf")
def export_monthly_report_pdf(
    project_id: int,
    year: int,
    month: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Generate monthly report PDF for the given year/month. No form — data from daily reports in that month."""
    if not psvc.get_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    from calendar import monthrange
    first = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    last = date(year, month, last_day)
    reports = (
        db.query(Report)
        .options(
            selectinload(Report.workforce),
            selectinload(Report.work_items),
            selectinload(Report.materials),
            selectinload(Report.issues),
        )
        .filter(
            Report.project_id == project_id,
            Report.report_type == "daily",
            Report.report_date >= first,
            Report.report_date <= last,
        )
        .order_by(Report.report_date)
        .all()
    )
    project = db.query(Project).filter(Project.id == project_id).first()
    project_name = project.name if project else f"Project {project_id}"
    period_label = first.strftime("%B %Y")
    payload = _aggregate_reports_payload(reports) if reports else {
        "report_date": str(first),
        "created_by_name": None,
        "weather": "", "temperature": None, "shift_start": None, "shift_end": None, "notes": "",
        "workforce": [], "work_items": [], "materials": [], "issues": [],
    }
    payload["report_date"] = str(first)
    pdf_bytes = render_monthly_report_pdf(project_name, payload, period_label)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="monthly-report-{year}-{month:02d}-{project_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.post("/reports/{report_id}/photos", response_model=dict)
async def upload_report_photo(
    report_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    caption: str = Form(default=""),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.is_locked:
        raise HTTPException(status_code=400, detail="Cannot add photos to a locked report")
    report_dir = REPORT_UPLOAD_ROOT / str(report_id)
    report_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "photo.jpg").suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")
    import uuid
    filename = f"{uuid.uuid4().hex}{ext}"
    path = report_dir / filename
    content = await file.read()
    path.write_bytes(content)
    photo_url = f"/uploads/reports/{report_id}/{filename}"
    photo = ReportPhoto(
        report_id=report_id,
        photo_url=photo_url,
        caption=caption or None,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return {
        "id": photo.id,
        "photo_url": photo.photo_url,
        "caption": photo.caption,
        "taken_at": photo.taken_at.isoformat(),
    }
