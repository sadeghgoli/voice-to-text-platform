from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.domain.catalog import TERMINAL_STATUSES
from app.models.entities import Job
from app.services.settings_store import get_settings_map
from app.services.storage import LocalStorage
from app.services.transcriptions import storage_root

log = structlog.get_logger()


def cleanup_storage(db: Session) -> None:
    settings_map = get_settings_map(db, refresh=True)
    storage = LocalStorage(storage_root(settings_map))
    now = utcnow()
    audio_cutoff = now - timedelta(hours=int(settings_map["audio_retention_hours"]))
    rows = db.scalars(
        select(Job).where(
            Job.audio_deleted_at.is_(None),
            Job.completed_at.is_not(None),
            Job.completed_at < audio_cutoff,
            Job.status.in_(TERMINAL_STATUSES),
        )
    ).all()
    for job in rows:
        storage.delete_file(job.stored_path)
        storage.delete_file(job.normalized_path)
        folder = Path(job.stored_path).parent
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
        job.audio_deleted_at = now
    if rows:
        db.commit()
        log.info("retention.audio_deleted", count=len(rows))

    result_cutoff = now - timedelta(days=int(settings_map["retention_days"]))
    old_ids = db.scalars(
        select(Job.id).where(
            Job.completed_at.is_not(None),
            Job.completed_at < result_cutoff,
            Job.status.in_(TERMINAL_STATUSES),
        )
    ).all()
    if old_ids:
        db.execute(delete(Job).where(Job.id.in_(old_ids)))
        db.commit()
        log.info("retention.results_deleted", count=len(old_ids))
