"""Workers, equipment, task_resources. Section 5.1."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade: Mapped[str] = mapped_column(String(100), nullable=False)
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    availability: Mapped[str] = mapped_column(String(20), nullable=False)  # Available, Assigned, On Leave
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    daily_cost: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # Available, Assigned, Under Maintenance
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TaskResource(Base):
    __tablename__ = "task_resources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[int] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # worker, equipment
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
