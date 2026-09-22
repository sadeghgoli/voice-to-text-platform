from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AudioProcessingError, JobCancelled
from app.core.time import utcnow
from app.models.entities import Job, SttModel, UsageRecord
from app.queue.client import cancel_requested, clear_cancel, enqueue_delayed
from app.services.audio import normalize_audio
from app.services.presenters import new_segment
from app.services.settings_store import get_settings_map
from app.services.storage import LocalStorage
from app.services.transcriptions import storage_root
from app.services.webhooks import deliver_webhook
from app.stt.engine import TranscribeOptions
from app.stt.registry import registry

log = structlog.get_logger()
RETRY_DELAYS = (5, 15, 45)


def process_job(job_id: str, device: str) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        _process(db, uuid.UUID(job_id), device)
    except Exception as exc:
        log.exception("worker.unhandled", job_id=job_id, error=str(exc))
    finally:
        db.close()


def _process(db: Session, job_id: uuid.UUID, device: str) -> None:
    claimed = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == "queued")
        .values(status="processing", progress=5, started_at=utcnow())
    )
    db.commit()
    if claimed.rowcount == 0:
        log.info("worker.skip", job_id=str(job_id))
        return

    job = db.get(Job, job_id)
    if job is None:
        return
    if job.created_at and job.started_at:
        job.queue_time_ms = max(0, int((job.started_at - job.created_at).total_seconds() * 1000))
        db.commit()
    log.info("worker.start", job_id=str(job.id), model=job.model_name, priority=job.priority)

    try:
        if _should_cancel(db, job):
            _finish_cancelled(db, job)
            return
        normalized = _prepare_audio(db, job)
        job.normalized_path = str(normalized)
        job.progress = 25
        db.commit()
        if _should_cancel(db, job):
            _finish_cancelled(db, job)
            return
        _transcribe(db, job, device, normalized)
        _finish_success(db, job)
    except JobCancelled:
        _finish_cancelled(db, job)
    except AudioProcessingError as exc:
        log.error("worker.audio_error", job_id=str(job.id), error=str(exc), permanent=exc.permanent)
        if exc.permanent:
            _finish_failed(db, job, str(exc))
        else:
            _retry_or_fail(db, job, str(exc))
    except Exception as exc:
        log.exception("worker.job_error", job_id=str(job.id), error=str(exc))
        _retry_or_fail(db, job, "خطای موقت در پردازش صوت.")


def _prepare_audio(db: Session, job: Job) -> Path:
    settings_map = get_settings_map(db)
    storage = LocalStorage(storage_root(settings_map))
    source = Path(job.stored_path)
    if not source.is_file():
        raise AudioProcessingError("فایل صوتی پیدا نشد.", permanent=True)
    target = storage.normalized_path(str(job.id))
    timeout = max(120, int((job.duration_seconds or 60) * 4))
    normalize_audio(source, target, timeout=timeout)
    return target


def _transcribe(db: Session, job: Job, device: str, audio_path: Path) -> None:
    model = db.scalar(select(SttModel).where(SttModel.name == job.model_name))
    if model is None or not model.is_active:
        raise AudioProcessingError("مدل در دسترس نیست.", permanent=True)
    options_raw = job.options or {}
    language = None if options_raw.get("language_mode") == "auto" else job.language
    options = TranscribeOptions(
        language=language,
        task=options_raw.get("task") or job.task or "transcribe",
        beam_size=int(options_raw.get("beam_size") or 5),
        temperature=float(options_raw.get("temperature") or 0),
        vad_filter=bool(options_raw.get("vad_filter", True)),
        word_timestamps=bool(options_raw.get("word_timestamps", True)),
        initial_prompt=options_raw.get("initial_prompt"),
    )
    duration = job.duration_seconds or 0
    last_progress = {"value": 25}

    def on_progress(end_sec: float) -> None:
        if cancel_requested(job.id):
            raise JobCancelled()
        if duration <= 0:
            return
        progress = 25 + int(min(end_sec / duration, 1) * 70)
        if progress >= last_progress["value"] + 5:
            last_progress["value"] = progress
            job.progress = min(progress, 95)
            db.commit()

    result = registry.transcribe(model, device, str(audio_path), options, on_progress=on_progress)
    if _should_cancel(db, job):
        raise JobCancelled()
    job.segments.clear()
    for index, segment in enumerate(result.segments):
        job.segments.append(new_segment(job.id, index, segment))
    job.text_result = result.text
    job.detected_language = result.language
    if result.duration and not job.duration_seconds:
        job.duration_seconds = result.duration
    log.info(
        "worker.transcribed",
        job_id=str(job.id),
        language=result.language,
        segments=len(result.segments),
    )


def _finish_success(db: Session, job: Job) -> None:
    if _should_cancel(db, job):
        _finish_cancelled(db, job)
        return
    finished = utcnow()
    job.status = "completed"
    job.progress = 100
    job.completed_at = finished
    job.error_message = None
    job.processing_time_ms = _elapsed_ms(job.started_at, finished)
    _add_usage(db, job, success=True)
    db.commit()
    clear_cancel(job.id)
    log.info("worker.completed", job_id=str(job.id), processing_time_ms=job.processing_time_ms)
    deliver_webhook(db, job, "transcription.completed")


def _finish_failed(db: Session, job: Job, message: str) -> None:
    finished = utcnow()
    job.status = "failed"
    job.error_message = message[:2000]
    job.completed_at = finished
    job.processing_time_ms = _elapsed_ms(job.started_at, finished)
    _add_usage(db, job, success=False)
    db.commit()
    log.error("worker.failed", job_id=str(job.id), error=job.error_message)
    deliver_webhook(db, job, "transcription.failed")


def _finish_cancelled(db: Session, job: Job) -> None:
    job.status = "cancelled"
    job.completed_at = utcnow()
    job.processing_time_ms = _elapsed_ms(job.started_at, job.completed_at)
    db.commit()
    clear_cancel(job.id)
    log.info("worker.cancelled", job_id=str(job.id))
    deliver_webhook(db, job, "transcription.cancelled")


def _retry_or_fail(db: Session, job: Job, message: str) -> None:
    db.refresh(job)
    if job.status == "cancelled":
        return
    next_try = job.retry_count + 1
    if next_try <= job.max_retries:
        job.retry_count = next_try
        job.status = "queued"
        job.progress = 0
        job.started_at = None
        job.error_message = message[:2000]
        db.commit()
        delay = RETRY_DELAYS[min(next_try - 1, len(RETRY_DELAYS) - 1)]
        enqueue_delayed(job.id, delay)
        log.warning("worker.retry", job_id=str(job.id), retry=next_try, delay=delay)
        return
    _finish_failed(db, job, message)


def _should_cancel(db: Session, job: Job) -> bool:
    if cancel_requested(job.id):
        return True
    current = db.scalar(select(Job.status).where(Job.id == job.id))
    return current == "cancelled"


def _add_usage(db: Session, job: Job, *, success: bool) -> None:
    db.add(
        UsageRecord(
            api_key_id=job.api_key_id,
            client_id=job.client_id,
            job_id=job.id,
            audio_seconds=job.duration_seconds or 0,
            success=success,
            processing_time_ms=job.processing_time_ms,
        )
    )


def _elapsed_ms(started: datetime | None, finished: datetime | None) -> int | None:
    if started is None or finished is None:
        return None
    return max(0, int((finished - started).total_seconds() * 1000))
