from __future__ import annotations

import json
import signal
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import structlog
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.redis_client import HEARTBEAT_KEY, HOST_HISTORY_KEY, HOST_STATS_KEY, get_redis
from app.core.time import utcnow
from app.db.session import SessionLocal, engine
from app.models.entities import Job, SttModel
from app.queue.client import enqueue, is_paused, promote_delayed
from app.services.settings_store import get_settings_map
from app.stt.registry import registry
from app.worker.gpu import collect_host_stats, log_gpu_banner, resolve_device
from app.worker.maintenance import cleanup_storage
from app.worker.processor import process_job

log = structlog.get_logger()


class STTWorker:
    def __init__(self) -> None:
        self._stop = False
        self.device = "cpu"

    def request_stop(self, *_args) -> None:
        self._stop = True

    def run(self) -> None:
        signal.signal(signal.SIGINT, self.request_stop)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self.request_stop)
        self._wait_until_ready()
        self.device = self._boot_model()
        threading.Thread(target=self._heartbeat_loop, name="heartbeat", daemon=True).start()
        threading.Thread(target=self._cleanup_loop, name="cleanup", daemon=True).start()
        log.info("worker.ready", device=self.device, models=registry.loaded_models())
        self._loop()

    def _wait_until_ready(self) -> None:
        for attempt in range(30):
            try:
                get_redis().ping()
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                return
            except Exception as exc:
                log.warning("worker.waiting_dependencies", attempt=attempt, error=str(exc))
                time.sleep(2)
        raise SystemExit("پایگاه داده یا Redis در دسترس نیست.")

    def _boot_model(self) -> str:
        db = SessionLocal()
        try:
            settings_map = get_settings_map(db, refresh=True)
            requested = settings_map.get("gpu_device") or "auto"
            if requested == "auto":
                requested = get_settings().device
            device = resolve_device(str(requested))
            stats = collect_host_stats(device)
            log_gpu_banner(stats)
            default_name = str(settings_map["default_model"])
            model = db.scalar(select(SttModel).where(SttModel.name == default_name, SttModel.is_active.is_(True)))
            if model is None:
                model = db.scalar(select(SttModel).where(SttModel.is_default.is_(True), SttModel.is_active.is_(True)))
            if model is None:
                raise SystemExit("هیچ مدل فعالی برای بارگذاری وجود ندارد.")
            registry.warmup(model, device)
            return device
        finally:
            db.close()

    def _loop(self) -> None:
        pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt-job")
        futures: set = set()
        while not self._stop:
            self._reap(futures)
            promote_delayed(self._requeue)
            if is_paused():
                time.sleep(1)
                continue
            limit = self._concurrency()
            if len(futures) >= limit:
                time.sleep(0.3)
                continue
            from app.queue.client import pop_next

            job_id = pop_next(timeout=2)
            if not job_id:
                continue
            if is_paused():
                self._requeue(job_id)
                time.sleep(1)
                continue
            futures.add(pool.submit(process_job, job_id, self.device))
        log.info("worker.stopping")
        pool.shutdown(wait=True)

    def _reap(self, futures: set) -> None:
        done = {item for item in futures if item.done()}
        for item in done:
            futures.remove(item)
            error = item.exception()
            if error:
                log.error("worker.future_failed", error=str(error))

    def _concurrency(self) -> int:
        db = SessionLocal()
        try:
            value = int(get_settings_map(db)["max_concurrent_jobs"])
        except Exception:
            value = 1
        finally:
            db.close()
        return max(1, min(4, value))

    def _requeue(self, job_id: str) -> None:
        db = SessionLocal()
        try:
            job = db.get(Job, uuid.UUID(job_id))
            if job is not None and job.status == "queued":
                enqueue(job)
        finally:
            db.close()

    def _heartbeat_loop(self) -> None:
        while not self._stop:
            try:
                stats = collect_host_stats(self.device)
                stats["loaded_models"] = registry.loaded_models()
                stats["paused"] = is_paused()
                raw = json.dumps(stats, ensure_ascii=False)
                client = get_redis()
                client.set(HEARTBEAT_KEY, utcnow().isoformat(), ex=15)
                client.set(HOST_STATS_KEY, raw, ex=30)
                client.lpush(HOST_HISTORY_KEY, raw)
                client.ltrim(HOST_HISTORY_KEY, 0, 719)
            except Exception as exc:
                log.warning("worker.heartbeat_failed", error=str(exc))
            time.sleep(5)

    def _cleanup_loop(self) -> None:
        while not self._stop:
            db = SessionLocal()
            try:
                cleanup_storage(db)
            except Exception as exc:
                log.error("retention.failed", error=str(exc))
            finally:
                db.close()
            for _ in range(120):
                if self._stop:
                    return
                time.sleep(5)


def main() -> None:
    setup_logging()
    STTWorker().run()


if __name__ == "__main__":
    main()
