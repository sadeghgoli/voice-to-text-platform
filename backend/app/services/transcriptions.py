from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, AudioProcessingError
from app.core.time import utcnow
from app.models.entities import ApiKey, Job, SttModel
from app.queue.client import enqueue
from app.services.audio import probe_duration
from app.services.audit import write_audit
from app.services.settings_store import get_settings_map
from app.services.storage import LocalStorage, assert_mime
from app.services.validators import (
    ensure_allowed_extension,
    normalize_language,
    parse_bool,
    sanitize_filename,
    validate_model_name,
    validate_webhook_url,
)

log = structlog.get_logger()


def storage_root(settings_map: dict) -> str:
    configured = settings_map.get("storage_path") or ""
    if isinstance(configured, str) and configured.strip():
        if ".." in Path(configured).parts:
            raise AppError("validation_error", "مسیر ذخیره‌سازی نامعتبر است.", 422)
        return configured.strip()
    return get_settings().storage_path


def _allows(allowed: list | None, value: str | None) -> bool:
    if not allowed:
        return True
    if value is None:
        return False
    return value in allowed


def _used_audio(db: Session, key_id: uuid.UUID, since) -> float:
    total = db.scalar(
        select(func.coalesce(func.sum(Job.duration_seconds), 0.0)).where(
            Job.api_key_id == key_id,
            Job.created_at >= since,
            Job.status.in_(("queued", "processing", "completed")),
        )
    )
    return float(total or 0)


async def accept_transcription(
    db: Session,
    api_key: ApiKey,
    upload: UploadFile,
    *,
    language: str | None,
    model: str | None,
    priority: int | None,
    webhook_url: str | None,
    task: str | None,
    beam_size: int | None,
    temperature: float | None,
    vad_filter: str | bool | None,
    word_timestamps: str | bool | None,
    initial_prompt: str | None,
    content_length: int | None,
    ip: str | None = None,
) -> Job:
    settings_map = get_settings_map(db)
    max_bytes = int(settings_map["max_upload_mb"]) * 1024 * 1024
    if content_length is not None and content_length > max_bytes + 2 * 1024 * 1024:
        raise AppError("payload_too_large", "حجم فایل از سقف مجاز بیشتر است.", 413)

    filename = sanitize_filename(upload.filename)
    ext = ensure_allowed_extension(filename)
    model_name = validate_model_name((model or settings_map["default_model"]).strip())
    stt_model = db.scalar(select(SttModel).where(SttModel.name == model_name))
    if stt_model is None or not stt_model.is_active:
        raise AppError("validation_error", "مدل انتخاب‌شده فعال نیست.", 422)
    if not _allows(api_key.allowed_models, model_name):
        raise AppError("forbidden", "این کلید اجازه استفاده از مدل انتخاب‌شده را ندارد.", 403)

    requested = normalize_language(language)
    if requested is None:
        requested = normalize_language(str(settings_map["default_language"])) or "fa"
    language_mode = "auto" if requested == "auto" else "explicit"
    stored_language = None if requested == "auto" else requested
    if not _allows(api_key.allowed_languages, requested):
        raise AppError("forbidden", "این کلید اجازه استفاده از زبان انتخاب‌شده را ندارد.", 403)

    chosen_priority = int(settings_map["default_priority"] if priority is None else priority)
    if chosen_priority < 1 or chosen_priority > 10:
        raise AppError("validation_error", "اولویت باید بین ۱ و ۱۰ باشد.", 422)
    chosen_task = (task or "transcribe").strip().lower()
    if chosen_task not in {"transcribe", "translate"}:
        raise AppError("validation_error", "وظیفه باید transcribe یا translate باشد.", 422)
    chosen_beam = int(settings_map["beam_size"] if beam_size is None else beam_size)
    if chosen_beam < 1 or chosen_beam > 10:
        raise AppError("validation_error", "beam_size باید بین ۱ و ۱۰ باشد.", 422)
    chosen_temperature = float(settings_map["temperature"] if temperature is None else temperature)
    if chosen_temperature < 0 or chosen_temperature > 1:
        raise AppError("validation_error", "temperature باید بین ۰ و ۱ باشد.", 422)
    chosen_vad = parse_bool(vad_filter)
    if chosen_vad is None:
        chosen_vad = bool(settings_map["vad_filter"])
    chosen_words = parse_bool(word_timestamps)
    if chosen_words is None:
        chosen_words = bool(settings_map["word_timestamps"])
    prompt = (initial_prompt or "").strip()
    if len(prompt) > 500:
        raise AppError("validation_error", "initial_prompt بیش از حد طولانی است.", 422)
    if not prompt and stored_language == "fa":
        prompt = str(settings_map["persian_initial_prompt"] or "")
    webhook = validate_webhook_url(webhook_url)

    job_id = uuid.uuid4()
    storage = LocalStorage(storage_root(settings_map))
    destination = storage.original_path(str(job_id), ext)
    size = 0
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise AppError("payload_too_large", "حجم فایل از سقف مجاز بیشتر است.", 413)
                handle.write(chunk)
        if size == 0:
            raise AppError("validation_error", "فایل خالی است.", 422)
        mime = assert_mime(destination, ext)
        try:
            duration = probe_duration(destination)
        except AudioProcessingError as exc:
            raise AppError("validation_error", str(exc), 422) from exc
        max_duration = int(settings_map["max_audio_duration_seconds"])
        if duration > max_duration:
            raise AppError("audio_too_long", "مدت صوت از سقف مجاز بیشتر است.", 422)
        _enforce_quota(db, api_key, duration)
    except Exception:
        storage.delete_file(str(destination))
        raise

    job = Job(
        id=job_id,
        client_id=api_key.client_id,
        api_key_id=api_key.id,
        filename=filename,
        stored_path=str(destination),
        mime_type=mime,
        file_size=size,
        duration_seconds=duration,
        language=stored_language,
        task=chosen_task,
        model_name=model_name,
        priority=chosen_priority,
        status="queued",
        progress=0,
        webhook_url=webhook,
        options={
            "task": chosen_task,
            "beam_size": chosen_beam,
            "temperature": chosen_temperature,
            "vad_filter": chosen_vad,
            "word_timestamps": chosen_words,
            "initial_prompt": prompt or None,
            "language_mode": language_mode,
        },
        max_retries=int(settings_map["max_retries"]),
        created_at=utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        enqueue(job)
    except Exception as exc:
        job.status = "failed"
        job.error_message = "صف در دسترس نیست."
        job.completed_at = utcnow()
        db.commit()
        log.error("queue.enqueue_failed", job_id=str(job.id), error=str(exc))
        raise AppError("service_unavailable", "صف در دسترس نیست.", 503) from exc
    log.info(
        "job.created",
        job_id=str(job.id),
        client_id=str(job.client_id),
        model=job.model_name,
        language=job.language,
        duration=job.duration_seconds,
        priority=job.priority,
    )
    record_audit_for_job(db, api_key, job, ip)
    return job


def _enforce_quota(db: Session, api_key: ApiKey, duration: float) -> None:
    now = utcnow()
    if api_key.daily_audio_limit_seconds is not None:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if _used_audio(db, api_key.id, start) + duration > api_key.daily_audio_limit_seconds:
            raise AppError("quota_exceeded", "سقف صوت روزانه این کلید پر شده است.", 429)
    if api_key.monthly_audio_limit_seconds is not None:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if _used_audio(db, api_key.id, start) + duration > api_key.monthly_audio_limit_seconds:
            raise AppError("quota_exceeded", "سقف صوت ماهانه این کلید پر شده است.", 429)


def record_audit_for_job(db: Session, api_key: ApiKey, job: Job, ip: str | None) -> None:
    write_audit(
        db,
        actor_type="api_key",
        actor_id=str(api_key.id),
        action="job.create",
        resource_type="job",
        resource_id=str(job.id),
        details={"filename": job.filename, "model": job.model_name},
        ip=ip,
    )
    db.commit()
