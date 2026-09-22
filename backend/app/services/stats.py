from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.redis_client import HOST_HISTORY_KEY, get_redis
from app.core.time import utcnow
from app.models.entities import ApiClient, Job
from app.queue.client import is_paused, queue_length
from app.services.health import gpu_health


def _since(range_key: str):
    now = utcnow()
    if range_key == "24h":
        return now - timedelta(hours=24), "hour"
    if range_key == "30d":
        return now - timedelta(days=30), "day"
    if range_key == "day":
        return now - timedelta(days=1), "hour"
    if range_key == "month":
        return now - timedelta(days=30), "day"
    return now - timedelta(days=7), "day"


def dashboard_summary(db: Session) -> dict:
    grouped = dict(db.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    total_audio = db.scalar(select(func.coalesce(func.sum(Job.duration_seconds), 0.0)).where(Job.status == "completed"))
    avg_processing = db.scalar(select(func.avg(Job.processing_time_ms)).where(Job.status == "completed"))
    hour_ago = utcnow() - timedelta(hours=1)
    jobs_per_hour = db.scalar(select(func.count()).select_from(Job).where(Job.created_at >= hour_ago))
    week_ago = utcnow() - timedelta(days=7)
    avg_wait = db.scalar(
        select(func.avg(Job.queue_time_ms)).where(Job.queue_time_ms.is_not(None), Job.created_at >= week_ago)
    )
    gpu = gpu_health()
    return {
        "total_jobs": int(sum(grouped.values())),
        "queued_jobs": int(grouped.get("queued", 0)),
        "processing_jobs": int(grouped.get("processing", 0)),
        "completed_jobs": int(grouped.get("completed", 0)),
        "failed_jobs": int(grouped.get("failed", 0)),
        "cancelled_jobs": int(grouped.get("cancelled", 0)),
        "total_audio_seconds": float(total_audio or 0),
        "queue_length": _safe_queue_length(),
        "paused": _safe_paused(),
        "avg_processing_ms": None if avg_processing is None else round(float(avg_processing)),
        "avg_waiting_ms": None if avg_wait is None else round(float(avg_wait)),
        "jobs_per_hour": int(jobs_per_hour or 0),
        "gpu": gpu.get("gpu"),
        "cpu": gpu.get("cpu"),
        "memory": gpu.get("memory"),
        "worker": gpu.get("status"),
    }


def dashboard_series(db: Session, range_key: str) -> dict:
    start, bucket = _since(range_key if range_key in {"24h", "7d", "30d"} else "7d")
    created = func.date_trunc(bucket, Job.created_at)
    rows = db.execute(
        select(created, func.count(Job.id), func.coalesce(func.sum(Job.duration_seconds), 0.0))
        .where(Job.created_at >= start)
        .group_by(created)
        .order_by(created)
    ).all()
    finished = func.date_trunc(bucket, Job.completed_at)
    processing_rows = db.execute(
        select(finished, func.avg(Job.processing_time_ms))
        .where(Job.completed_at.is_not(None), Job.completed_at >= start, Job.status == "completed")
        .group_by(finished)
        .order_by(finished)
    ).all()
    usage_rows = db.execute(
        select(ApiClient.name, func.count(Job.id))
        .join(ApiClient, ApiClient.id == Job.client_id)
        .where(Job.created_at >= start)
        .group_by(ApiClient.name)
        .order_by(func.count(Job.id).desc())
    ).all()
    return {
        "jobs_over_time": [
            {"t": item[0].isoformat(), "count": int(item[1]), "audio_seconds": float(item[2])} for item in rows
        ],
        "processing_time": [
            {"t": item[0].isoformat(), "avg_ms": round(float(item[1]))} for item in processing_rows if item[0] and item[1] is not None
        ],
        "api_usage": [{"client": item[0], "requests": int(item[1])} for item in usage_rows],
        "gpu_utilization": _gpu_history(),
    }


def usage_report(db: Session, range_key: str) -> dict:
    start, bucket = _since(range_key if range_key in {"day", "week", "month"} else "week")
    stamp = func.date_trunc(bucket, Job.created_at)
    by_client = db.execute(
        select(
            ApiClient.id,
            ApiClient.name,
            func.count(Job.id),
            func.count(Job.id).filter(Job.status == "completed"),
            func.count(Job.id).filter(Job.status == "failed"),
            func.coalesce(func.sum(Job.duration_seconds), 0.0),
            func.avg(Job.processing_time_ms),
        )
        .join(ApiClient, ApiClient.id == Job.client_id)
        .where(Job.created_at >= start)
        .group_by(ApiClient.id, ApiClient.name)
        .order_by(func.count(Job.id).desc())
    ).all()
    series = db.execute(
        select(
            stamp,
            func.count(Job.id),
            func.coalesce(func.sum(Job.duration_seconds), 0.0),
            func.count(Job.id).filter(Job.status == "completed"),
            func.count(Job.id).filter(Job.status == "failed"),
        )
        .where(Job.created_at >= start)
        .group_by(stamp)
        .order_by(stamp)
    ).all()
    clients = []
    totals = {"requests": 0, "successful": 0, "failed": 0, "audio_seconds": 0.0, "avg_processing_ms": None}
    weighted = 0.0
    weight = 0
    for row in by_client:
        avg_ms = None if row[6] is None else round(float(row[6]))
        clients.append(
            {
                "client_id": str(row[0]),
                "client": row[1],
                "requests": int(row[2]),
                "successful": int(row[3]),
                "failed": int(row[4]),
                "audio_seconds": float(row[5]),
                "audio_minutes": round(float(row[5]) / 60, 2),
                "avg_processing_ms": avg_ms,
            }
        )
        totals["requests"] += int(row[2])
        totals["successful"] += int(row[3])
        totals["failed"] += int(row[4])
        totals["audio_seconds"] += float(row[5])
        if avg_ms is not None:
            weighted += avg_ms * int(row[2])
            weight += int(row[2])
    if weight:
        totals["avg_processing_ms"] = round(weighted / weight)
    totals["audio_minutes"] = round(totals["audio_seconds"] / 60, 2)
    return {
        "range": range_key if range_key in {"day", "week", "month"} else "week",
        "totals": totals,
        "clients": clients,
        "series": [
            {
                "t": item[0].isoformat(),
                "requests": int(item[1]),
                "audio_seconds": float(item[2]),
                "successful": int(item[3]),
                "failed": int(item[4]),
            }
            for item in series
            if item[0] is not None
        ],
    }


def _gpu_history() -> list[dict]:
    try:
        raw_items = get_redis().lrange(HOST_HISTORY_KEY, 0, 179)
    except Exception:
        return []
    points = []
    for raw in reversed(raw_items):
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        gpu = item.get("gpu") or {}
        points.append(
            {
                "t": item.get("updated_at"),
                "gpu": gpu.get("utilization_percent"),
                "vram_percent": _vram_percent(gpu),
                "cpu": (item.get("cpu") or {}).get("percent"),
                "ram": (item.get("memory") or {}).get("percent"),
            }
        )
    return points


def _vram_percent(gpu: dict) -> float | None:
    used = gpu.get("vram_used_mb")
    total = gpu.get("vram_total_mb")
    if not used or not total:
        return None
    return round(used / total * 100, 1)


def _safe_queue_length() -> int | None:
    try:
        return queue_length()
    except Exception:
        return None


def _safe_paused() -> bool | None:
    try:
        return is_paused()
    except Exception:
        return None
