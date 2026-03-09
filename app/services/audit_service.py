"""Audit logging. NFR-SEC-007."""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def log_audit(
    db: Session,
    user_id: int,
    action: str,
    table_name: str,
    record_id: int,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
    )
    db.add(entry)
    db.commit()
