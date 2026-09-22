from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.catalog import DEFAULT_SETTINGS, MODEL_CATALOG
from app.models.entities import SttModel, SystemSetting
from app.core.time import utcnow


def seed() -> None:
    db = SessionLocal()
    try:
        for item in MODEL_CATALOG:
            existing = db.scalar(select(SttModel).where(SttModel.name == item["name"]))
            if existing is None:
                db.add(SttModel(**item))
        for key, value in DEFAULT_SETTINGS.items():
            if db.get(SystemSetting, key) is None:
                db.add(SystemSetting(key=key, value=value, updated_at=utcnow()))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
