from fastapi import APIRouter

from app.api.admin import auth, clients, dashboard, jobs, keys, logs, models, queue, settings, system, usage

router = APIRouter()
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(jobs.router)
router.include_router(queue.router)
router.include_router(clients.router)
router.include_router(keys.router)
router.include_router(models.router)
router.include_router(usage.router)
router.include_router(system.router)
router.include_router(logs.router)
router.include_router(settings.router)
