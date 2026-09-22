from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_admin
from app.core.errors import AppError
from app.db.session import get_db
from app.models.entities import ApiClient, ApiKey, Job, User
from app.services.audit import write_audit

router = APIRouter(prefix="/clients", tags=["Admin Clients"])


class ClientBody(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    owner_name: str = Field(default="", max_length=200)
    status: str = "active"


def _stats(db: Session) -> dict:
    rows = db.execute(
        select(
            Job.client_id,
            func.count(Job.id),
            func.count(Job.id).filter(Job.status == "completed"),
            func.count(Job.id).filter(Job.status == "failed"),
            func.coalesce(func.sum(Job.duration_seconds), 0.0),
            func.max(Job.created_at),
        ).group_by(Job.client_id)
    ).all()
    return {
        row[0]: {
            "total_requests": int(row[1]),
            "successful_requests": int(row[2]),
            "failed_requests": int(row[3]),
            "audio_seconds": float(row[4]),
            "last_request": row[5].isoformat() if row[5] else None,
        }
        for row in rows
    }


def _dump(client: ApiClient, stats: dict, key_count: int) -> dict:
    item = stats.get(client.id, {})
    return {
        "id": str(client.id),
        "name": client.name,
        "description": client.description,
        "owner_name": client.owner_name,
        "status": client.status,
        "api_keys": key_count,
        "total_requests": item.get("total_requests", 0),
        "successful_requests": item.get("successful_requests", 0),
        "failed_requests": item.get("failed_requests", 0),
        "audio_seconds": item.get("audio_seconds", 0),
        "last_request": item.get("last_request"),
        "created_at": client.created_at.isoformat(),
    }


@router.get("", summary="List API clients")
def list_clients(_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    clients = db.scalars(select(ApiClient).order_by(ApiClient.created_at.desc())).all()
    counts = dict(db.execute(select(ApiKey.client_id, func.count(ApiKey.id)).group_by(ApiKey.client_id)).all())
    stats = _stats(db)
    return {"items": [_dump(client, stats, int(counts.get(client.id, 0))) for client in clients]}


@router.post("", status_code=201, summary="Create an API client")
def create_client(body: ClientBody, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if body.status not in {"active", "disabled"}:
        raise AppError("validation_error", "وضعیت کلاینت نامعتبر است.", 422)
    client = ApiClient(name=body.name.strip(), description=body.description.strip(), owner_name=body.owner_name.strip(), status=body.status)
    db.add(client)
    db.commit()
    db.refresh(client)
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="client.create", resource_type="api_client", resource_id=str(client.id), ip=client_ip(request))
    db.commit()
    return _dump(client, {}, 0)


@router.patch("/{client_id}", summary="Update an API client")
def update_client(
    client_id: uuid.UUID,
    body: ClientBody,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    client = db.get(ApiClient, client_id)
    if client is None:
        raise AppError("not_found", "کلاینت پیدا نشد.", 404)
    if body.status not in {"active", "disabled"}:
        raise AppError("validation_error", "وضعیت کلاینت نامعتبر است.", 422)
    client.name = body.name.strip()
    client.description = body.description.strip()
    client.owner_name = body.owner_name.strip()
    client.status = body.status
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="client.update", resource_type="api_client", resource_id=str(client.id), ip=client_ip(request))
    db.commit()
    key_count = int(db.scalar(select(func.count()).select_from(ApiKey).where(ApiKey.client_id == client.id)) or 0)
    return _dump(client, _stats(db), key_count)
