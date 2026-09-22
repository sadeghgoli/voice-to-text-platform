from fastapi import APIRouter

from app.api.v1 import health, models, queue, transcriptions, usage

router = APIRouter()
router.include_router(transcriptions.router)
router.include_router(usage.router)
router.include_router(models.router)
router.include_router(queue.router)
router.include_router(health.router)
