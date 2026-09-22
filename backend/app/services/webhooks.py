from __future__ import annotations

import time

import httpx
import structlog
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.entities import Job, WebhookDelivery
from app.services.settings_store import get_settings_map

log = structlog.get_logger()


def build_payload(job: Job, event: str) -> dict:
    segments = [
        {"start": segment.start_sec, "end": segment.end_sec, "text": segment.text}
        for segment in (job.segments or [])
    ]
    return {
        "event": event,
        "job_id": str(job.id),
        "status": job.status,
        "text": job.text_result or "",
        "duration": job.duration_seconds,
        "language": job.detected_language or job.language,
        "error_message": job.error_message,
        "segments": segments,
    }


def deliver_webhook(db: Session, job: Job, event: str) -> None:
    if not job.webhook_url:
        return
    settings = get_settings_map(db)
    timeout = float(settings.get("webhook_timeout_seconds") or 10)
    payload = build_payload(job, event)
    delivery = WebhookDelivery(
        job_id=job.id,
        url=job.webhook_url,
        event=event,
        payload=payload,
        status="pending",
    )
    db.add(delivery)
    db.commit()
    last_error = None
    for attempt in range(1, 4):
        try:
            response = httpx.post(job.webhook_url, json=payload, timeout=timeout)
            delivery.attempts = attempt
            delivery.response_code = response.status_code
            if 200 <= response.status_code < 300:
                delivery.status = "sent"
                delivery.delivered_at = utcnow()
                db.commit()
                log.info("webhook.sent", job_id=str(job.id), event=event, status_code=response.status_code)
                return
            last_error = response.text[:500]
            delivery.last_error = last_error
        except Exception as exc:
            last_error = str(exc)[:500]
            delivery.attempts = attempt
            delivery.last_error = last_error
            log.warning("webhook.attempt_failed", job_id=str(job.id), attempt=attempt, error=last_error)
        db.commit()
        time.sleep(attempt)
    delivery.status = "failed"
    db.commit()
    log.error("webhook.failed", job_id=str(job.id), event=event, error=last_error)
