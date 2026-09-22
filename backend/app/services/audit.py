from __future__ import annotations

import structlog
from sqlalchemy.orm import Session

from app.models.entities import AuditLog

log = structlog.get_logger()


def write_audit(
    db: Session,
    *,
    actor_type: str,
    actor_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip=ip,
        )
    )
    log.info("audit", action=action, resource_type=resource_type, resource_id=resource_id, actor_type=actor_type)
