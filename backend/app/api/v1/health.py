from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.health import database_health, gpu_health, overall_health, queue_health

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Overall health")
def health(db: Session = Depends(get_db)):
    payload = overall_health(db)
    code = 200 if payload["status"] != "unhealthy" else 503
    return JSONResponse(status_code=code, content=payload)


@router.get("/health/gpu", summary="GPU health")
def health_gpu():
    return gpu_health()


@router.get("/health/queue", summary="Queue health")
def health_queue():
    payload = queue_health()
    code = 200 if payload["status"] != "unhealthy" else 503
    return JSONResponse(status_code=code, content=payload)


@router.get("/health/database", summary="Database health")
def health_database(db: Session = Depends(get_db)):
    status = database_health(db)
    return JSONResponse(status_code=200 if status == "healthy" else 503, content={"status": status})
