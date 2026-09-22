from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_admin
from app.core.errors import AppError
from app.db.session import get_db
from app.models.entities import SttModel, User
from app.services.audit import write_audit
from app.services.settings_store import upsert_settings
from app.services.validators import validate_whisper_id

router = APIRouter(prefix="/models", tags=["Admin Models"])


class ModelPatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    whisper_model_id: str | None = None
    is_active: bool | None = None
    compute_type: str | None = None


def _dump(model: SttModel) -> dict:
    return {
        "id": str(model.id),
        "name": model.name,
        "display_name": model.display_name,
        "engine": model.engine,
        "whisper_model_id": model.whisper_model_id,
        "language": model.language_label,
        "size": model.size_label,
        "vram_mb": model.vram_mb,
        "compute_type": model.compute_type,
        "status": "active" if model.is_active else "inactive",
        "is_active": model.is_active,
        "default": model.is_default,
    }


@router.get("", summary="List speech models")
def list_models(_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(SttModel).order_by(SttModel.is_default.desc(), SttModel.name)).all()
    return {"items": [_dump(row) for row in rows]}


@router.post("/{model_id}/default", summary="Set the default model")
def set_default(model_id: uuid.UUID, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    model = db.get(SttModel, model_id)
    if model is None:
        raise AppError("not_found", "مدل پیدا نشد.", 404)
    db.execute(update(SttModel).values(is_default=False))
    model.is_default = True
    model.is_active = True
    db.commit()
    upsert_settings(db, {"default_model": model.name})
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="model.default", resource_type="model", resource_id=str(model.id), ip=client_ip(request))
    db.commit()
    return _dump(model)


@router.patch("/{model_id}", summary="Update a model")
def patch_model(
    model_id: uuid.UUID,
    body: ModelPatch,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    model = db.get(SttModel, model_id)
    if model is None:
        raise AppError("not_found", "مدل پیدا نشد.", 404)
    if body.display_name is not None:
        model.display_name = body.display_name.strip()
    if body.whisper_model_id is not None:
        model.whisper_model_id = validate_whisper_id(body.whisper_model_id)
    if body.compute_type is not None:
        if body.compute_type not in {"float16", "int8", "int8_float16", "float32"}:
            raise AppError("validation_error", "compute_type نامعتبر است.", 422)
        model.compute_type = body.compute_type
    if body.is_active is not None:
        if model.is_default and not body.is_active:
            raise AppError("conflict", "مدل پیش‌فرض را نمی‌توان غیرفعال کرد.", 409)
        model.is_active = body.is_active
    write_audit(db, actor_type="admin", actor_id=str(admin.id), action="model.update", resource_type="model", resource_id=str(model.id), ip=client_ip(request))
    db.commit()
    return _dump(model)
