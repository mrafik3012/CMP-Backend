"""Document model. Section 5.1."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_kb: Mapped[float] = mapped_column(Float, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    tag: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Contract, Blueprint, RFI, Inspection Report, Change Order, Invoice, Other
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
