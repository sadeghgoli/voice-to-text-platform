from __future__ import annotations

import json
import uuid
from datetime import datetime

from app.core.errors import AppError
from app.models.entities import Job, JobSegment
from app.stt.formats import segments_to_srt, segments_to_vtt


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def segment_dicts(job: Job, *, with_words: bool = True) -> list[dict]:
    items = []
    for segment in job.segments or []:
        payload = {
            "start": segment.start_sec,
            "end": segment.end_sec,
            "text": segment.text,
        }
        if with_words:
            payload["words"] = segment.words
        items.append(payload)
    return items


def job_created(job: Job) -> dict:
    return {"success": True, "job_id": str(job.id), "status": job.status}


def job_status(job: Job) -> dict:
    payload = {
        "success": True,
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "filename": job.filename,
        "language": job.detected_language or job.language,
        "model": job.model_name,
        "priority": job.priority,
        "duration": job.duration_seconds,
        "error_message": job.error_message,
        "created_at": iso(job.created_at),
        "started_at": iso(job.started_at),
        "completed_at": iso(job.completed_at),
        "processing_time": None if job.processing_time_ms is None else round(job.processing_time_ms / 1000, 3),
    }
    if job.status == "completed":
        payload["text"] = job.text_result or ""
    return payload


def job_admin(job: Job, *, include_segments: bool = True) -> dict:
    queue_seconds = None if job.queue_time_ms is None else round(job.queue_time_ms / 1000, 3)
    processing_seconds = None if job.processing_time_ms is None else round(job.processing_time_ms / 1000, 3)
    return {
        "id": str(job.id),
        "filename": job.filename,
        "client_id": str(job.client_id),
        "client_name": job.client.name if job.client is not None else None,
        "api_key_id": str(job.api_key_id),
        "api_key_name": job.api_key.name if job.api_key is not None else None,
        "api_key_prefix": job.api_key.key_prefix if job.api_key is not None else None,
        "language": job.language,
        "detected_language": job.detected_language,
        "model": job.model_name,
        "priority": job.priority,
        "status": job.status,
        "progress": job.progress,
        "duration": job.duration_seconds,
        "file_size": job.file_size,
        "mime_type": job.mime_type,
        "task": job.task,
        "options": job.options or {},
        "text": job.text_result,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "webhook_url": job.webhook_url,
        "created_at": iso(job.created_at),
        "started_at": iso(job.started_at),
        "completed_at": iso(job.completed_at),
        "processing_time": processing_seconds,
        "queue_time": queue_seconds,
        "audio_deleted_at": iso(job.audio_deleted_at),
        "segments": segment_dicts(job) if include_segments else [],
    }


def render_job_result(job: Job, fmt: str) -> tuple[str, str, str]:
    segments = segment_dicts(job, with_words=fmt == "json")
    if fmt == "txt":
        return job.text_result or "", "text/plain; charset=utf-8", "txt"
    if fmt == "srt":
        return segments_to_srt(segments), "application/x-subrip; charset=utf-8", "srt"
    if fmt == "vtt":
        return segments_to_vtt(segments), "text/vtt; charset=utf-8", "vtt"
    if fmt == "json":
        body = json.dumps(
            {
                "job_id": str(job.id),
                "language": job.detected_language or job.language,
                "duration": job.duration_seconds,
                "text": job.text_result or "",
                "segments": segments,
            },
            ensure_ascii=False,
            indent=2,
        )
        return body, "application/json; charset=utf-8", "json"
    raise AppError("validation_error", "فرمت خروجی باید txt، json، srt یا vtt باشد.", 422)


def new_segment(job_id: uuid.UUID, index: int, payload: dict) -> JobSegment:
    return JobSegment(
        job_id=job_id,
        segment_index=index,
        start_sec=float(payload["start"]),
        end_sec=float(payload["end"]),
        text=payload.get("text") or "",
        words=payload.get("words"),
    )
