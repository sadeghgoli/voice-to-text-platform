from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit
from app.db.session import get_db
from app.models.entities import ApiKey, SttModel

router = APIRouter(tags=["Models"])


@router.get("/models", summary="List models available to this API key")
def list_models(api_key: ApiKey = Depends(enforce_rate_limit), db: Session = Depends(get_db)):
    rows = db.scalars(select(SttModel).where(SttModel.is_active.is_(True)).order_by(SttModel.name)).all()
    allowed = set(api_key.allowed_models or [])
    models = []
    for row in rows:
        if allowed and row.name not in allowed:
            continue
        models.append(
            {
                "name": row.name,
                "display_name": row.display_name,
                "language": row.language_label,
                "size": row.size_label,
                "vram_mb": row.vram_mb,
                "status": "active",
                "default": row.is_default,
            }
        )
    return {"success": True, "models": models}
