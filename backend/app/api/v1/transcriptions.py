from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import client_ip, enforce_rate_limit
from app.core.errors import AppError
from app.db.session import get_db
from app.models.entities import ApiKey, Job
from app.services.audit import write_audit
from app.services.jobs import cancel_job
from app.services.presenters import job_created, job_status, render_job_result
from app.services.transcriptions import accept_transcription

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


def _owned_job(db: Session, job_id: uuid.UUID, api_key: ApiKey) -> Job:
    job = db.scalar(
        select(Job)
        .options(selectinload(Job.segments))
        .where(Job.id == job_id, Job.api_key_id == api_key.id)
    )
    if job is None:
        raise AppError("not_found", "درخواست پیدا نشد.", 404)
    return job


@router.post("", status_code=202, summary="Create a transcription job")
async def create_transcription(
    request: Request,
    file: UploadFile = File(..., description="Audio or video file"),
    language: str | None = Form(None, description="BCP-47 language such as fa. Omit to use the system default. Send auto to detect."),
    model: str | None = Form(None, description="Model name: large-v3, medium, or small"),
    priority: int | None = Form(None, description="1 (low) to 10 (high)"),
    webhook_url: str | None = Form(None),
    task: str | None = Form(None, description="transcribe or translate"),
    beam_size: int | None = Form(None),
    temperature: float | None = Form(None),
    vad_filter: str | None = Form(None),
    word_timestamps: str | None = Form(None),
    initial_prompt: str | None = Form(None),
    api_key: ApiKey = Depends(enforce_rate_limit),
    db: Session = Depends(get_db),
):
    """Queue an audio file and return immediately. Poll the job or wait for the webhook."""
    content_length = request.headers.get("content-length")
    job = await accept_transcription(
        db,
        api_key,
        file,
        language=language,
        model=model,
        priority=priority,
        webhook_url=webhook_url,
        task=task,
        beam_size=beam_size,
        temperature=temperature,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
        initial_prompt=initial_prompt,
        content_length=int(content_length) if content_length and content_length.isdigit() else None,
        ip=client_ip(request),
    )
    return job_created(job)


@router.get("/{job_id}", summary="Get transcription status")
def get_transcription(
    job_id: uuid.UUID,
    api_key: ApiKey = Depends(enforce_rate_limit),
    db: Session = Depends(get_db),
):
    return job_status(_owned_job(db, job_id, api_key))


@router.get("/{job_id}/result", summary="Download transcription result")
def get_result(
    job_id: uuid.UUID,
    format: str = Query("json", pattern="^(txt|json|srt|vtt)$"),
    api_key: ApiKey = Depends(enforce_rate_limit),
    db: Session = Depends(get_db),
):
    job = _owned_job(db, job_id, api_key)
    if job.status != "completed":
        raise AppError("conflict", "نتیجه هنوز آماده نیست.", 409)
    body, media_type, extension = render_job_result(job, format)
    filename = f"{job.id}.{extension}"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{job_id}", summary="Cancel a transcription")
def delete_transcription(
    job_id: uuid.UUID,
    request: Request,
    api_key: ApiKey = Depends(enforce_rate_limit),
    db: Session = Depends(get_db),
):
    job = _owned_job(db, job_id, api_key)
    cancel_job(db, job)
    write_audit(
        db,
        actor_type="api_key",
        actor_id=str(api_key.id),
        action="job.cancel",
        resource_type="job",
        resource_id=str(job.id),
        ip=client_ip(request),
    )
    db.commit()
    return job_status(job)
