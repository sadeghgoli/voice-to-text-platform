import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.redis_client import HOST_STATS_KEY, get_redis
from app.db.session import get_db
from app.models.entities import User
from app.services.health import overall_health
from app.services.stats import _gpu_history

router = APIRouter(prefix="/system", tags=["Admin System"])


@router.get("", summary="System and GPU status")
def system(_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    raw = None
    try:
        raw = get_redis().get(HOST_STATS_KEY)
    except Exception:
        raw = None
    stats = json.loads(raw) if raw else None
    return {"health": overall_health(db), "stats": stats, "history": _gpu_history()}
