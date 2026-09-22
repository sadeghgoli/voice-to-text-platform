from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit
from app.core.time import utcnow
from app.db.session import get_db
from app.models.entities import ApiKey, Job
from app.services.settings_store import get_settings_map

router = APIRouter(tags=["Usage"])


@router.get("/usage", summary="Usage for the current API key")
def usage(api_key: ApiKey = Depends(enforce_rate_limit), db: Session = Depends(get_db)):
    now = utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    settings_map = get_settings_map(db)

    def audio(since) -> float:
        value = db.scalar(
            select(func.coalesce(func.sum(Job.duration_seconds), 0.0)).where(
                Job.api_key_id == api_key.id,
                Job.created_at >= since,
                Job.status.in_(("queued", "processing", "completed")),
            )
        )
        return float(value or 0)

    def requests(since, status: str | None = None) -> int:
        stmt = select(func.count()).select_from(Job).where(Job.api_key_id == api_key.id, Job.created_at >= since)
        if status:
            stmt = stmt.where(Job.status == status)
        return int(db.scalar(stmt) or 0)

    return {
        "success": True,
        "requests_today": requests(day_start),
        "successful_today": requests(day_start, "completed"),
        "failed_today": requests(day_start, "failed"),
        "audio_seconds_today": audio(day_start),
        "audio_seconds_month": audio(month_start),
        "limits": {
            "rate_limit_per_minute": api_key.rate_limit_per_minute or int(settings_map["rate_limit_per_minute"]),
            "daily_audio_limit_seconds": api_key.daily_audio_limit_seconds,
            "monthly_audio_limit_seconds": api_key.monthly_audio_limit_seconds,
        },
    }
