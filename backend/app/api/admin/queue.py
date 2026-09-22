from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_admin
from app.db.session import get_db
from app.models.entities import Job, User
from app.core.redis_client import HEARTBEAT_KEY, get_redis
from app.queue.client import is_paused, queue_length, set_paused
from app.services.audit import write_audit
from app.services.stats import dashboard_summary

router = APIRouter(prefix="/queue", tags=["Admin Queue"])


@router.get("", summary="Queue dashboard")
def queue_dashboard(_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    summary = dashboard_summary(db)
    try:
        paused = is_paused()
        length = queue_length()
        online = bool(get_redis().get(HEARTBEAT_KEY))
    except Exception:
        paused, length, online = None, None, False
    counts = {
        "queued": summary["queued_jobs"],
        "processing": summary["processing_jobs"],
        "completed": summary["completed_jobs"],
        "failed": summary["failed_jobs"],
        "cancelled": summary["cancelled_jobs"],
    }
    recent = db.execute(select(Job.status, func.count()).group_by(Job.status)).all()
    return {
        "paused": paused,
        "queue_length": length,
        "counts": counts,
        "status_rows": [{"status": status, "count": count} for status, count in recent],
        "avg_waiting_ms": summary["avg_waiting_ms"],
        "avg_processing_ms": summary["avg_processing_ms"],
        "worker_online": online,
    }


@router.post("/pause", summary="Pause the queue")
def pause(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    set_paused(True)
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="queue.pause", resource_type="queue", ip=client_ip(request))
    db.commit()
    return {"paused": True}


@router.post("/resume", summary="Resume the queue")
def resume(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    set_paused(False)
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="queue.resume", resource_type="queue", ip=client_ip(request))
    db.commit()
    return {"paused": False}
