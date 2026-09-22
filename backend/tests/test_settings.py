from app.services.settings_store import validate_settings_update
import pytest
from app.core.errors import AppError


def test_settings_ranges():
    cleaned = validate_settings_update({"max_concurrent_jobs": 2, "default_language": "fa", "vad_filter": True})
    assert cleaned["max_concurrent_jobs"] == 2
    assert cleaned["default_language"] == "fa"


def test_settings_reject_unknown_and_unsafe_path():
    with pytest.raises(AppError):
        validate_settings_update({"not_a_setting": 1})
    with pytest.raises(AppError):
        validate_settings_update({"storage_path": "/data/../etc"})
