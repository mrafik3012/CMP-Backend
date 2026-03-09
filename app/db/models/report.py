"""Report and related models per Report Templates Requirements 3.1."""
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # daily, weekly, monthly
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)  # draft, submitted, approved
    weather: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    shift_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    shift_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workforce: Mapped[list["ReportWorkforce"]] = relationship(
        "ReportWorkforce", back_populates="report", cascade="all, delete-orphan"
    )
    work_items: Mapped[list["ReportWorkItem"]] = relationship(
        "ReportWorkItem", back_populates="report", cascade="all, delete-orphan"
    )
    materials: Mapped[list["ReportMaterial"]] = relationship(
        "ReportMaterial", back_populates="report", cascade="all, delete-orphan"
    )
    issues: Mapped[list["ReportIssue"]] = relationship(
        "ReportIssue", back_populates="report", cascade="all, delete-orphan"
    )
    photos: Mapped[list["ReportPhoto"]] = relationship(
        "ReportPhoto", back_populates="report", cascade="all, delete-orphan"
    )


class ReportWorkforce(Base):
    __tablename__ = "report_workforce"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    trade: Mapped[str] = mapped_column(String(50), nullable=False)
    present: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    absent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    report: Mapped["Report"] = relationship("Report", back_populates="workforce")


class ReportWorkItem(Base):
    __tablename__ = "report_work_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    boq_item: Mapped[str | None] = mapped_column(String(50), nullable=True)
    progress_today: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    progress_cumulative: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)

    report: Mapped["Report"] = relationship("Report", back_populates="work_items")


class ReportMaterial(Base):
    __tablename__ = "report_materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # received, pending, delayed

    report: Mapped["Report"] = relationship("Report", back_populates="materials")


class ReportIssue(Base):
    __tablename__ = "report_issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    issue_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # delay, safety, quality, material
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low, medium, high
    responsible_party: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    report: Mapped["Report"] = relationship("Report", back_populates="issues")


class ReportPhoto(Base):
    __tablename__ = "report_photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    photo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(11, 8), nullable=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    report: Mapped["Report"] = relationship("Report", back_populates="photos")


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    baseline_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, on_track, delayed, complete
