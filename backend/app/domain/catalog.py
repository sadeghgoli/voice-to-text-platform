from __future__ import annotations

DEFAULT_SETTINGS: dict = {
    "default_model": "large-v3",
    "default_language": "fa",
    "max_upload_mb": 500,
    "max_audio_duration_seconds": 7200,
    "max_concurrent_jobs": 1,
    "default_priority": 5,
    "retention_days": 90,
    "audio_retention_hours": 24,
    "storage_path": "",
    "temp_path": "",
    "gpu_device": "auto",
    "webhook_timeout_seconds": 10,
    "rate_limit_per_minute": 100,
    "beam_size": 5,
    "temperature": 0.0,
    "vad_filter": True,
    "word_timestamps": True,
    "persian_initial_prompt": "این یک گفتار فارسی است.",
    "max_retries": 3,
}

MODEL_CATALOG: list[dict] = [
    {
        "name": "large-v3",
        "display_name": "Whisper Large V3",
        "engine": "faster-whisper",
        "whisper_model_id": "large-v3",
        "language_label": "Multilingual",
        "size_label": "~3 GB",
        "vram_mb": 3100,
        "compute_type": "float16",
        "is_active": True,
        "is_default": True,
    },
    {
        "name": "medium",
        "display_name": "Whisper Medium",
        "engine": "faster-whisper",
        "whisper_model_id": "medium",
        "language_label": "Multilingual",
        "size_label": "~1.5 GB",
        "vram_mb": 1600,
        "compute_type": "float16",
        "is_active": True,
        "is_default": False,
    },
    {
        "name": "small",
        "display_name": "Whisper Small",
        "engine": "faster-whisper",
        "whisper_model_id": "small",
        "language_label": "Multilingual",
        "size_label": "~500 MB",
        "vram_mb": 700,
        "compute_type": "float16",
        "is_active": True,
        "is_default": False,
    },
    {
        "name": "persian-custom",
        "display_name": "مدل اختصاصی فارسی",
        "engine": "faster-whisper",
        "whisper_model_id": "persian-custom",
        "language_label": "fa",
        "size_label": "سفارشی",
        "vram_mb": 3000,
        "compute_type": "float16",
        "is_active": False,
        "is_default": False,
    },
]

TERMINAL_STATUSES = ("completed", "failed", "cancelled")
ACTIVE_QUEUE_STATUSES = ("queued", "processing")
SCORE_BASE = 10**13
