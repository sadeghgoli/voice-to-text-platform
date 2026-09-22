from __future__ import annotations

import subprocess
from pathlib import Path

import structlog

from app.core.errors import AudioProcessingError

log = structlog.get_logger()


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioProcessingError("پردازش صوت بیش از حد طول کشید.", permanent=False) from exc
    except FileNotFoundError as exc:
        raise AudioProcessingError("FFmpeg روی سرور نصب نیست.", permanent=True) from exc


def probe_duration(path: Path, ffprobe_bin: str = "ffprobe") -> float:
    result = _run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        timeout=60,
    )
    if result.returncode != 0:
        log.error("ffmpeg.probe_failed", stderr=result.stderr[-500:])
        raise AudioProcessingError("خواندن مدت فایل صوتی ممکن نشد.", permanent=True)
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise AudioProcessingError("مدت فایل صوتی نامعتبر است.", permanent=True) from exc
    if duration <= 0:
        raise AudioProcessingError("فایل صوتی خالی است.", permanent=True)
    return duration


def normalize_audio(source: Path, target: Path, ffmpeg_bin: str = "ffmpeg", timeout: int = 600) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    result = _run(
        [
            ffmpeg_bin,
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        timeout=timeout,
    )
    if result.returncode != 0 or not target.is_file():
        log.error("ffmpeg.convert_failed", stderr=result.stderr[-800:])
        raise AudioProcessingError("تبدیل صوت ناموفق بود.", permanent=True)
    log.info("ffmpeg.normalized", source=source.name, target=target.name)
