from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utcnow
from app.models.entities import Job
from app.queue.client import clear_cancel, enqueue, remove, request_cancel
from app.services.webhooks import deliver_webhook


def cancel_job(db: Session, job: Job) -> Job:
    if job.status in {"completed", "failed"}:
        raise AppError("conflict", "این درخواست دیگر قابل لغو نیست.", 409)
    if job.status == "cancelled":
        return job
    request_cancel(job.id)
    remove(job.id)
    if job.status == "queued":
        job.status = "cancelled"
        job.completed_at = utcnow()
        db.commit()
        deliver_webhook(db, job, "transcription.cancelled")
        return job
    db.commit()
    return job


def retry_job(db: Session, job: Job) -> Job:
    if job.status not in {"failed", "cancelled"}:
        raise AppError("conflict", "فقط درخواست ناموفق یا لغوشده قابل تلاش مجدد است.", 409)
    if job.audio_deleted_at is not None or not Path(job.stored_path).is_file():
        raise AppError("conflict", "فایل صوتی این درخواست دیگر موجود نیست.", 409)
    clear_cancel(job.id)
    job.status = "queued"
    job.progress = 0
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.processing_time_ms = None
    job.queue_time_ms = None
    job.retry_count = 0
    job.text_result = None
    job.detected_language = None
    job.segments.clear()
    db.commit()
    enqueue(job)
    db.refresh(job)
    return job
