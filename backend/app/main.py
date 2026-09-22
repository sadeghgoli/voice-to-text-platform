from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin.router import router as admin_router
from app.api.middleware import RequestLogMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import setup_logging

log = structlog.get_logger()

DESCRIPTION = """
Central speech-to-text API for Persian and other languages.

## Authentication
Send `Authorization: Bearer sk_stt_...` or `X-API-Key`. Admin routes use a separate JWT from `POST /api/v1/admin/auth/login`.

## Upload
`POST /api/v1/transcriptions` accepts wav, mp3, m4a, ogg, flac, aac, mp4, webm, and mov. The response is immediate and contains `job_id`.

## Job status
`GET /api/v1/transcriptions/{id}` returns `queued`, `processing`, `completed`, `failed`, or `cancelled`, plus progress.

## Result
`GET /api/v1/transcriptions/{id}/result?format=txt|json|srt|vtt`

## Webhook
Pass `webhook_url` when creating a job. The platform POSTs `transcription.completed`, `transcription.failed`, or `transcription.cancelled`.

## API keys
Keys are created in the admin panel, shown once, and stored as a SHA-256 hash.

## Errors
`{"success": false, "error": {"code": "...", "message": "..."}}`
"""


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1/admin")

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"success": False, "error": {"code": "validation_error", "message": "درخواست نامعتبر است.", "details": exc.errors()}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("api.unhandled", error=str(exc))
        return JSONResponse(status_code=500, content={"success": False, "error": {"code": "internal_error", "message": "خطای داخلی سرور."}})

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"service": "stt-platform", "docs": "/docs", "health": "/health"}

    return app


app = create_app()
