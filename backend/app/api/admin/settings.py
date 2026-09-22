from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_admin
from app.core.errors import AppError
from app.db.session import get_db
from app.models.entities import SttModel, User
from app.services.audit import write_audit
from app.services.settings_store import get_settings_map, upsert_settings, validate_settings_update

router = APIRouter(prefix="/settings", tags=["Admin Settings"])


@router.get("", summary="System settings")
def get_settings(_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {"items": get_settings_map(db, refresh=True)}


@router.put("", summary="Update system settings")
def put_settings(body: dict, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    cleaned = validate_settings_update(body)
    if "default_model" in cleaned:
        model = db.scalar(select(SttModel).where(SttModel.name == cleaned["default_model"], SttModel.is_active.is_(True)))
        if model is None:
            raise AppError("validation_error", "مدل پیش‌فرض باید یک مدل فعال باشد.", 422)
    updated = upsert_settings(db, cleaned)
    write_audit(
        db,
        actor_type="admin",
        actor_id=str(admin.id),
        action="settings.update",
        resource_type="settings",
        details={"keys": sorted(cleaned)},
        ip=client_ip(request),
    )
    db.commit()
    return {"items": updated}
