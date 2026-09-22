from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import client_ip, get_current_admin
from app.core.errors import AppError
from app.db.session import get_db
from app.models.entities import Job, User
from app.services.audit import write_audit
from app.services.jobs import cancel_job, retry_job
from app.services.presenters import job_admin, render_job_result

router = APIRouter(prefix="/jobs", tags=["Admin Jobs"])


def _job_or_404(db: Session, job_id: uuid.UUID) -> Job:
    job = db.scalar(
        select(Job)
        .options(selectinload(Job.segments), selectinload(Job.client), selectinload(Job.api_key))
        .where(Job.id == job_id)
    )
    if job is None:
        raise AppError("not_found", "درخواست پیدا نشد.", 404)
    return job


@router.get("", summary="List jobs")
def list_jobs(
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    model: str | None = None,
    language: str | None = None,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    filters = []
    if status:
        filters.append(Job.status == status)
    if client_id:
        filters.append(Job.client_id == client_id)
    if model:
        filters.append(Job.model_name == model)
    if language:
        filters.append(or_(Job.language == language, Job.detected_language == language))
    if date_from:
        filters.append(Job.created_at >= date_from)
    if date_to:
        filters.append(Job.created_at <= date_to)
    if q:
        term = f"%{q.replace('%', '').replace('_', '')}%"
        filters.append(or_(Job.filename.ilike(term), cast(Job.id, String).ilike(term)))
    total = int(db.scalar(select(func.count()).select_from(Job).where(*filters)) or 0)
    rows = db.scalars(
        select(Job)
        .options(selectinload(Job.client), selectinload(Job.api_key))
        .where(*filters)
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [job_admin(row, include_segments=False) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{job_id}", summary="Job details")
def job_detail(job_id: uuid.UUID, _admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return job_admin(_job_or_404(db, job_id))


@router.get("/{job_id}/result", summary="Download a job result")
def job_result(
    job_id: uuid.UUID,
    format: str = Query("json", pattern="^(txt|json|srt|vtt)$"),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, job_id)
    if job.status != "completed":
        raise AppError("conflict", "نتیجه هنوز آماده نیست.", 409)
    body, media_type, extension = render_job_result(job, format)
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{job.id}.{extension}"'},
    )


@router.post("/{job_id}/cancel", summary="Cancel a job")
def cancel(job_id: uuid.UUID, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    cancel_job(db, job)
    write_audit(
        db,
        actor_type="admin",
        actor_id=str(admin.id),
        action="job.cancel",
        resource_type="job",
        resource_id=str(job.id),
        ip=client_ip(request),
    )
    db.commit()
    return job_admin(job, include_segments=False)


@router.post("/{job_id}/retry", summary="Retry a failed job")
def retry(job_id: uuid.UUID, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    retry_job(db, job)
    write_audit(
        db,
        actor_type="admin",
        actor_id=str(admin.id),
        action="job.retry",
        resource_type="job",
        resource_id=str(job.id),
        ip=client_ip(request),
    )
    db.commit()
    return job_admin(job, include_segments=False)
