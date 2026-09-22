from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_admin
from app.core.errors import AppError
from app.core.security import generate_api_key, mask_api_key
from app.core.time import utcnow
from app.db.session import get_db
from app.models.entities import ApiClient, ApiKey, Job, User
from app.services.audit import write_audit
from app.services.settings_store import get_settings_map

router = APIRouter(prefix="/keys", tags=["Admin API Keys"])


class KeyBody(BaseModel):
    client_id: uuid.UUID
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=100000)
    daily_audio_limit_seconds: int | None = Field(default=None, ge=0)
    monthly_audio_limit_seconds: int | None = Field(default=None, ge=0)
    allowed_models: list[str] = Field(default_factory=list)
    allowed_languages: list[str] = Field(default_factory=list)


def _stats(db: Session) -> dict:
    rows = db.execute(
        select(
            Job.api_key_id,
            func.count(Job.id),
            func.count(Job.id).filter(Job.status == "completed"),
            func.count(Job.id).filter(Job.status == "failed"),
            func.coalesce(func.sum(Job.duration_seconds), 0.0),
        ).group_by(Job.api_key_id)
    ).all()
    return {
        row[0]: {
            "requests": int(row[1]),
            "successful": int(row[2]),
            "failed": int(row[3]),
            "audio_seconds": float(row[4]),
        }
        for row in rows
    }


def _dump(key: ApiKey, stats: dict, *, secret: str | None = None) -> dict:
    item = stats.get(key.id, {})
    payload = {
        "id": str(key.id),
        "client_id": str(key.client_id),
        "client_name": key.client.name if key.client is not None else None,
        "name": key.name,
        "description": key.description,
        "prefix": mask_api_key(key.key_prefix),
        "status": key.status,
        "rate_limit_per_minute": key.rate_limit_per_minute,
        "daily_audio_limit_seconds": key.daily_audio_limit_seconds,
        "monthly_audio_limit_seconds": key.monthly_audio_limit_seconds,
        "allowed_models": key.allowed_models or [],
        "allowed_languages": key.allowed_languages or [],
        "requests": item.get("requests", 0),
        "successful_requests": item.get("successful", 0),
        "failed_requests": item.get("failed", 0),
        "audio_seconds": item.get("audio_seconds", 0),
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "created_at": key.created_at.isoformat(),
    }
    if secret:
        payload["api_key"] = secret
    return payload


def _apply(key: ApiKey, body: KeyBody, default_rate: int) -> None:
    key.name = body.name.strip()
    key.description = body.description.strip()
    key.rate_limit_per_minute = body.rate_limit_per_minute or default_rate
    key.daily_audio_limit_seconds = body.daily_audio_limit_seconds
    key.monthly_audio_limit_seconds = body.monthly_audio_limit_seconds
    key.allowed_models = body.allowed_models or None
    key.allowed_languages = [item.strip().lower() for item in body.allowed_languages] or None


@router.get("", summary="List API keys")
def list_keys(_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    keys = db.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())).all()
    stats = _stats(db)
    return {"items": [_dump(key, stats) for key in keys]}


@router.post("", status_code=201, summary="Create an API key")
def create_key(body: KeyBody, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    client = db.get(ApiClient, body.client_id)
    if client is None:
        raise AppError("not_found", "کلاینت پیدا نشد.", 404)
    raw, digest, prefix = generate_api_key()
    key = ApiKey(client_id=client.id, key_hash=digest, key_prefix=prefix, status="active")
    _apply(key, body, int(get_settings_map(db)["rate_limit_per_minute"]))
    db.add(key)
    db.commit()
    db.refresh(key)
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="api_key.create", resource_type="api_key", resource_id=str(key.id), details={"prefix": prefix}, ip=client_ip(request))
    db.commit()
    return _dump(key, {}, secret=raw)


def _key_or_404(db: Session, key_id: uuid.UUID) -> ApiKey:
    key = db.get(ApiKey, key_id)
    if key is None:
        raise AppError("not_found", "کلید پیدا نشد.", 404)
    return key


@router.post("/{key_id}/disable", summary="Disable an API key")
def disable_key(key_id: uuid.UUID, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    key = _key_or_404(db, key_id)
    if key.status == "revoked":
        raise AppError("conflict", "کلید لغوشده را نمی‌توان فقط غیرفعال کرد.", 409)
    key.status = "disabled"
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="api_key.disable", resource_type="api_key", resource_id=str(key.id), ip=client_ip(request))
    db.commit()
    return _dump(key, _stats(db))


@router.post("/{key_id}/enable", summary="Enable an API key")
def enable_key(key_id: uuid.UUID, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    key = _key_or_404(db, key_id)
    if key.status == "revoked":
        raise AppError("conflict", "کلید لغوشده باید دوباره ساخته شود.", 409)
    key.status = "active"
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="api_key.enable", resource_type="api_key", resource_id=str(key.id), ip=client_ip(request))
    db.commit()
    return _dump(key, _stats(db))


@router.post("/{key_id}/revoke", summary="Revoke an API key")
def revoke_key(key_id: uuid.UUID, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    key = _key_or_404(db, key_id)
    key.status = "revoked"
    key.revoked_at = utcnow()
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="api_key.revoke", resource_type="api_key", resource_id=str(key.id), ip=client_ip(request))
    db.commit()
    return _dump(key, _stats(db))


@router.post("/{key_id}/regenerate", summary="Regenerate an API key")
def regenerate_key(key_id: uuid.UUID, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    key = _key_or_404(db, key_id)
    raw, digest, prefix = generate_api_key()
    key.key_hash = digest
    key.key_prefix = prefix
    key.status = "active"
    key.revoked_at = None
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="api_key.regenerate", resource_type="api_key", resource_id=str(key.id), details={"prefix": prefix}, ip=client_ip(request))
    db.commit()
    return _dump(key, _stats(db), secret=raw)
