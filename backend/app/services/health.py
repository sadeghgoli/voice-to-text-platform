from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.redis_client import HEARTBEAT_KEY, HOST_STATS_KEY, get_redis
from app.queue.client import is_paused, queue_length


def _redis_ok() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def database_health(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unhealthy"


def queue_health() -> dict:
    try:
        online = bool(get_redis().get(HEARTBEAT_KEY))
        return {
            "status": "healthy" if online else "degraded",
            "paused": is_paused(),
            "queue_length": queue_length(),
            "worker": "online" if online else "offline",
        }
    except Exception:
        return {"status": "unhealthy", "paused": None, "queue_length": None, "worker": "offline"}


def gpu_health() -> dict:
    try:
        raw = get_redis().get(HOST_STATS_KEY)
    except Exception:
        return {"status": "unhealthy", "gpu": None}
    if not raw:
        return {"status": "unknown", "gpu": None}
    stats = json.loads(raw)
    gpu = stats.get("gpu") or {}
    if gpu.get("device") == "cpu":
        state = "disabled"
    elif gpu.get("available"):
        state = "healthy"
    else:
        state = "unhealthy"
    return {"status": state, "gpu": gpu, "cpu": stats.get("cpu"), "memory": stats.get("memory")}


def overall_health(db: Session) -> dict:
    database = database_health(db)
    queue = queue_health()
    gpu = gpu_health()
    redis_ok = _redis_ok()
    parts = {
        "database": database,
        "queue": "unhealthy" if not redis_ok else queue["status"],
        "gpu": gpu["status"],
    }
    if database != "healthy" or not redis_ok:
        status = "unhealthy"
    elif queue["status"] != "healthy" or gpu["status"] == "unhealthy":
        status = "degraded"
    else:
        status = "healthy"
    return {"status": status, **parts, "worker": queue.get("worker")}
