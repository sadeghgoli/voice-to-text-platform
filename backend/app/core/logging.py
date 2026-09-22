from __future__ import annotations

import json
import logging
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.redis_client import LOG_KEY


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _redis_processor(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.core.redis_client import get_redis

        payload = _json_safe(event_dict)
        client = get_redis()
        client.lpush(LOG_KEY, json.dumps(payload, ensure_ascii=False))
        client.ltrim(LOG_KEY, 0, 1999)
    except Exception:
        pass
    return event_dict


def setup_logging() -> None:
    settings = get_settings()
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _redis_processor,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
