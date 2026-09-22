from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from app.core.errors import AppError

ALLOWED_EXTENSIONS = {
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".m4a": {"audio/mp4", "audio/x-m4a", "audio/m4a", "video/mp4"},
    ".ogg": {"audio/ogg", "application/ogg", "video/ogg"},
    ".flac": {"audio/flac", "audio/x-flac"},
    ".aac": {"audio/aac", "audio/x-aac"},
    ".mp4": {"video/mp4", "audio/mp4", "application/mp4"},
    ".webm": {"video/webm", "audio/webm"},
    ".mov": {"video/quicktime"},
}

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._\-\u0600-\u06FF ]+")
_MODEL_NAME = re.compile(r"^[A-Za-z0-9._:-]+$")


def sanitize_filename(name: str | None) -> str:
    raw = (name or "audio").replace("\\", "/").split("/")[-1]
    cleaned = _FILENAME_SAFE.sub("_", raw).strip("._ ")
    return (cleaned or "audio")[:180]


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower()


def ensure_allowed_extension(filename: str) -> str:
    ext = extension_of(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError("unsupported_media", "فرمت فایل پشتیبانی نمی‌شود.", 415)
    return ext


def ensure_allowed_mime(ext: str, mime: str | None) -> str:
    allowed = ALLOWED_EXTENSIONS.get(ext, set())
    if not mime:
        return next(iter(allowed))
    normalized = mime.lower().split(";")[0].strip()
    if normalized not in allowed:
        raise AppError("unsupported_media", "نوع فایل با پسوند آن هم‌خوان نیست.", 415)
    return normalized


def validate_webhook_url(url: str | None) -> str | None:
    if url is None or url.strip() == "":
        return None
    cleaned = url.strip()
    if len(cleaned) > 2000:
        raise AppError("validation_error", "آدرس وبهوک بیش از حد طولانی است.", 422)
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise AppError("validation_error", "آدرس وبهوک باید http یا https باشد.", 422)
    host = parsed.hostname.lower()
    if host in {"169.254.169.254", "metadata.google.internal"}:
        raise AppError("validation_error", "آدرس وبهوک مجاز نیست.", 422)
    return cleaned


def normalize_language(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    cleaned = value.strip().lower().replace("_", "-")
    if cleaned == "auto":
        return "auto"
    primary = cleaned.split("-", 1)[0]
    if not re.fullmatch(r"[a-z]{2,3}", primary):
        raise AppError("validation_error", "کد زبان نامعتبر است.", 422)
    return primary


def validate_model_name(value: str) -> str:
    if not _MODEL_NAME.fullmatch(value or ""):
        raise AppError("validation_error", "نام مدل نامعتبر است.", 422)
    return value


def validate_whisper_id(value: str) -> str:
    cleaned = (value or "").strip()
    parts = cleaned.replace("\\", "/").split("/")
    if not cleaned or ".." in parts or any(char in cleaned for char in "\n\r\0"):
        raise AppError("validation_error", "شناسه مدل نامعتبر است.", 422)
    if not re.fullmatch(r"[A-Za-z0-9._:/\-]+", cleaned):
        raise AppError("validation_error", "شناسه مدل نامعتبر است.", 422)
    return cleaned


def parse_bool(value: str | bool | None) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise AppError("validation_error", "مقدار بولین نامعتبر است.", 422)


def safe_path(root: Path, *parts: str) -> Path:
    base = root.resolve()
    candidate = base.joinpath(*parts).resolve()
    if candidate != base and base not in candidate.parents:
        raise AppError("validation_error", "مسیر فایل مجاز نیست.", 400)
    return candidate
