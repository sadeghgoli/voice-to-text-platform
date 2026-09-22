from __future__ import annotations

import time
import uuid

import structlog

from app.core.redis_client import CANCEL_PREFIX, DELAY_KEY, PAUSE_KEY, QUEUE_KEY, get_redis
from app.models.entities import Job
from app.queue.priority import queue_score

log = structlog.get_logger()


def enqueue(job: Job) -> None:
    client = get_redis()
    score = queue_score(job.priority, job.created_at)
    client.zadd(QUEUE_KEY, {str(job.id): score})
    log.info("queue.enqueue", job_id=str(job.id), priority=job.priority, score=score)


def enqueue_delayed(job_id: uuid.UUID | str, delay_seconds: int) -> None:
    available_at = time.time() + max(1, delay_seconds)
    get_redis().zadd(DELAY_KEY, {str(job_id): available_at})
    log.info("queue.delay", job_id=str(job_id), delay_seconds=delay_seconds)


def remove(job_id: uuid.UUID | str) -> None:
    client = get_redis()
    client.zrem(QUEUE_KEY, str(job_id))
    client.zrem(DELAY_KEY, str(job_id))


def request_cancel(job_id: uuid.UUID | str) -> None:
    get_redis().set(f"{CANCEL_PREFIX}{job_id}", "1", ex=60 * 60 * 24)


def cancel_requested(job_id: uuid.UUID | str) -> bool:
    return bool(get_redis().get(f"{CANCEL_PREFIX}{job_id}"))


def clear_cancel(job_id: uuid.UUID | str) -> None:
    get_redis().delete(f"{CANCEL_PREFIX}{job_id}")


def queue_length() -> int:
    return int(get_redis().zcard(QUEUE_KEY))


def is_paused() -> bool:
    return get_redis().get(PAUSE_KEY) == "1"


def set_paused(paused: bool) -> None:
    client = get_redis()
    if paused:
        client.set(PAUSE_KEY, "1")
        log.warning("queue.paused")
    else:
        client.delete(PAUSE_KEY)
        log.info("queue.resumed")


def pop_next(timeout: int = 2) -> str | None:
    item = get_redis().bzpopmax(QUEUE_KEY, timeout=timeout)
    if not item:
        return None
    _key, member, _score = item
    return str(member)


def promote_delayed(requeue) -> int:
    client = get_redis()
    now = time.time()
    ready = client.zrangebyscore(DELAY_KEY, 0, now)
    moved = 0
    for job_id in ready:
        removed = client.zrem(DELAY_KEY, job_id)
        if removed:
            requeue(str(job_id))
            moved += 1
    return moved
