import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.redis_client import LOG_KEY, get_redis
from app.db.session import get_db
from app.models.entities import AuditLog, User

router = APIRouter(prefix="/logs", tags=["Admin Logs"])


@router.get("", summary="Recent operational logs")
def logs(limit: int = Query(200, ge=1, le=500), _admin: User = Depends(get_current_admin)):
    try:
        raw_items = get_redis().lrange(LOG_KEY, 0, limit - 1)
    except Exception:
        raw_items = []
    items = []
    for raw in raw_items:
        try:
            items.append(json.loads(raw))
        except json.JSONDecodeError:
            items.append({"event": raw, "level": "info"})
    return {"items": items}


@router.get("/audit", summary="Audit log")
def audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total = int(db.scalar(select(func.count()).select_from(AuditLog)) or 0)
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "actor_type": row.actor_type,
                "actor_id": row.actor_id,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "metadata": row.details or {},
                "ip": row.ip,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
