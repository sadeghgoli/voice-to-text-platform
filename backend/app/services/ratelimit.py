from __future__ import annotations

import time
import uuid

from app.core.errors import AppError
from app.core.redis_client import get_redis


def allow_request(key_id: uuid.UUID, limit: int, window_seconds: int = 60) -> None:
    if limit <= 0:
        raise AppError("rate_limited", "محدودیت درخواست این کلید صفر است.", 429)
    now = time.time()
    redis_key = f"stt:rl:{key_id}"
    member = f"{now}:{uuid.uuid4()}"
    try:
        client = get_redis()
        pipe = client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
        pipe.zadd(redis_key, {member: now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds + 5)
        _, _, count, _ = pipe.execute()
    except Exception as exc:
        raise AppError("service_unavailable", "سرویس صف در دسترس نیست.", 503) from exc
    if int(count) > limit:
        raise AppError("rate_limited", "تعداد درخواست در دقیقه از حد مجاز گذشته است.", 429)
