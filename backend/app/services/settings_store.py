from __future__ import annotations

import time
from threading import Lock

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utcnow
from app.domain.catalog import DEFAULT_SETTINGS
from app.models.entities import SystemSetting
from app.services.validators import normalize_language, validate_model_name

log = structlog.get_logger()
_cache: dict = {"at": 0.0, "data": None}
_lock = Lock()


def get_settings_map(db: Session, *, refresh: bool = False) -> dict:
    now = time.monotonic()
    with _lock:
        if not refresh and _cache["data"] is not None and now - _cache["at"] < 3:
            return dict(_cache["data"])
    stored = {row.key: row.value for row in db.scalars(select(SystemSetting)).all()}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(stored)
    with _lock:
        _cache["at"] = now
        _cache["data"] = dict(merged)
    return merged


def invalidate_settings_cache() -> None:
    with _lock:
        _cache["at"] = 0.0
        _cache["data"] = None


def upsert_settings(db: Session, values: dict) -> dict:
    for key, value in values.items():
        row = db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value=value, updated_at=utcnow()))
        else:
            row.value = value
            row.updated_at = utcnow()
    db.commit()
    invalidate_settings_cache()
    log.info("settings.updated", keys=sorted(values))
    return get_settings_map(db, refresh=True)


def validate_settings_update(values: dict) -> dict:
    unknown = sorted(set(values) - set(DEFAULT_SETTINGS))
    if unknown:
        raise AppError("validation_error", "تنظیم ناشناخته ارسال شده است.", 422)
    cleaned: dict = {}
    for key, value in values.items():
        cleaned[key] = _coerce_setting(key, value)
    return cleaned


def _coerce_setting(key: str, value):
    ranges = {
        "max_upload_mb": (1, 5000),
        "max_audio_duration_seconds": (1, 86400),
        "max_concurrent_jobs": (1, 4),
        "default_priority": (1, 10),
        "retention_days": (1, 3650),
        "audio_retention_hours": (1, 8760),
        "webhook_timeout_seconds": (1, 120),
        "rate_limit_per_minute": (1, 100000),
        "beam_size": (1, 10),
        "max_retries": (0, 10),
    }
    if key in ranges:
        number = int(value)
        low, high = ranges[key]
        if number < low or number > high:
            raise AppError("validation_error", f"مقدار {key} خارج از محدوده است.", 422)
        return number
    if key == "temperature":
        number = float(value)
        if number < 0 or number > 1:
            raise AppError("validation_error", "temperature خارج از محدوده است.", 422)
        return number
    if key in {"vad_filter", "word_timestamps"}:
        if not isinstance(value, bool):
            raise AppError("validation_error", f"مقدار {key} باید بولین باشد.", 422)
        return value
    if key == "gpu_device":
        if value not in {"auto", "cuda", "cpu"}:
            raise AppError("validation_error", "gpu_device نامعتبر است.", 422)
        return value
    if key == "default_language":
        return normalize_language(str(value)) or "fa"
    if key == "default_model":
        return validate_model_name(str(value))
    if key in {"storage_path", "temp_path"}:
        text = str(value or "").strip()
        if ".." in text.replace("\\", "/").split("/"):
            raise AppError("validation_error", "مسیر تنظیمات نامعتبر است.", 422)
        return text
    if key == "persian_initial_prompt":
        text = str(value or "").strip()
        if len(text) > 500:
            raise AppError("validation_error", "پرامپت اولیه بیش از حد طولانی است.", 422)
        return text
    raise AppError("validation_error", "تنظیم پشتیبانی نمی‌شود.", 422)
