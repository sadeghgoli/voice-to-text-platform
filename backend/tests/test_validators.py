import pytest

from app.core.errors import AppError
from app.services.validators import (
    ensure_allowed_extension,
    sanitize_filename,
    validate_webhook_url,
    validate_whisper_id,
)


def test_sanitize_strips_path_and_unsafe_characters():
    assert sanitize_filename(r"..\..\etc\passwd.mp3") == "passwd.mp3"
    assert sanitize_filename("جلسه شورا.wav") == "جلسه شورا.wav"
    assert "/" not in sanitize_filename("a/b/c.mp3")


def test_rejects_unknown_extension():
    with pytest.raises(AppError) as exc:
        ensure_allowed_extension("payload.exe")
    assert exc.value.status_code == 415


def test_accepts_video_extensions():
    assert ensure_allowed_extension("meeting.MP4") == ".mp4"
    assert ensure_allowed_extension("clip.webm") == ".webm"


def test_webhook_blocks_metadata_host():
    with pytest.raises(AppError):
        validate_webhook_url("http://169.254.169.254/latest")
    assert validate_webhook_url("https://example.internal/hooks/stt") == "https://example.internal/hooks/stt"
    assert validate_webhook_url("   ") is None


def test_whisper_id_rejects_traversal():
    with pytest.raises(AppError):
        validate_whisper_id("../secrets")
    assert validate_whisper_id("large-v3") == "large-v3"
