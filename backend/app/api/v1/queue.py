from fastapi import APIRouter, Depends

from app.api.deps import enforce_rate_limit
from app.models.entities import ApiKey
from app.services.health import queue_health

router = APIRouter(tags=["Queue"])


@router.get("/queue/status", summary="Shared queue status")
def queue_status(_api_key: ApiKey = Depends(enforce_rate_limit)):
    payload = queue_health()
    return {"success": True, **payload}
