from __future__ import annotations

from datetime import datetime

from app.domain.catalog import SCORE_BASE


def clamp_priority(priority: int) -> int:
    return max(1, min(10, int(priority)))


def queue_score(priority: int, created_at: datetime) -> int:
    """Higher score is dequeued first. Same priority stays FIFO."""
    created_ms = int(created_at.timestamp() * 1000)
    bounded = max(0, min(SCORE_BASE - 1, created_ms))
    return clamp_priority(priority) * SCORE_BASE + (SCORE_BASE - bounded)
