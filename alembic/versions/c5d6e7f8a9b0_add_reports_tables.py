"""Add reports and project_milestones tables. Report Templates Requirements 3.1.

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("weather", sa.String(100), nullable=True),
        sa.Column("temperature", sa.Numeric(5, 2), nullable=True),
        sa.Column("shift_start", sa.Time(), nullable=True),
        sa.Column("shift_end", sa.Time(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_project_id", "reports", ["project_id"], unique=False)
    op.create_index("ix_reports_report_date", "reports", ["report_date"], unique=False)

    op.create_table(
        "report_workforce",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("trade", sa.String(50), nullable=False),
        sa.Column("present", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("absent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "report_work_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("task_name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("boq_item", sa.String(50), nullable=True),
        sa.Column("progress_today", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("progress_cumulative", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "report_materials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.String(50), nullable=True),
        sa.Column("supplier", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "report_issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("issue_type", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", sa.String(20), nullable=True),
        sa.Column("responsible_party", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "report_photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=False),
        sa.Column("caption", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
        sa.Column("taken_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "project_milestones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("milestone_name", sa.String(255), nullable=False),
        sa.Column("baseline_date", sa.Date(), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_milestones_project_id", "project_milestones", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_project_milestones_project_id", table_name="project_milestones")
    op.drop_table("project_milestones")
    op.drop_table("report_photos")
    op.drop_table("report_issues")
    op.drop_table("report_materials")
    op.drop_table("report_work_items")
    op.drop_table("report_workforce")
    op.drop_index("ix_reports_report_date", table_name="reports")
    op.drop_index("ix_reports_project_id", table_name="reports")
    op.drop_table("reports")
