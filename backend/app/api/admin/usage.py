from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.entities import User
from app.services.stats import usage_report

router = APIRouter(prefix="/usage", tags=["Admin Usage"])


@router.get("", summary="Usage report")
def usage(
    range_key: str = Query("week", alias="range", pattern="^(day|week|month)$"),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return usage_report(db, range_key)
