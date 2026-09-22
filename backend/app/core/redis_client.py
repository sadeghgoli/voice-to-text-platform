from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import get_settings

LOG_KEY = "stt:logs"
QUEUE_KEY = "stt:queue"
DELAY_KEY = "stt:delayed"
PAUSE_KEY = "stt:queue:paused"
HEARTBEAT_KEY = "stt:worker:heartbeat"
HOST_STATS_KEY = "stt:host:stats"
HOST_HISTORY_KEY = "stt:host:history"
CANCEL_PREFIX = "stt:cancel:"


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def reset_redis() -> None:
    get_redis.cache_clear()
