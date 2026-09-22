from datetime import datetime, timezone

from app.queue.priority import queue_score


def test_higher_priority_is_dequeued_first():
    created = datetime(2026, 9, 22, tzinfo=timezone.utc)
    assert queue_score(10, created) > queue_score(5, created)
    assert queue_score(5, created) > queue_score(1, created)


def test_same_priority_is_fifo():
    earlier = datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc)
    later = datetime(2026, 9, 22, 10, 5, tzinfo=timezone.utc)
    assert queue_score(5, earlier) > queue_score(5, later)


def test_priority_is_clamped():
    created = datetime(2026, 9, 22, tzinfo=timezone.utc)
    assert queue_score(100, created) == queue_score(10, created)
    assert queue_score(0, created) == queue_score(1, created)
