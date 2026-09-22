from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.entities import User
from app.services.stats import dashboard_series, dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


@router.get("", summary="Dashboard summary")
def summary(_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return dashboard_summary(db)


@router.get("/series", summary="Dashboard charts")
def series(
    range_key: str = Query("7d", alias="range", pattern="^(24h|7d|30d)$"),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return dashboard_series(db, range_key)
