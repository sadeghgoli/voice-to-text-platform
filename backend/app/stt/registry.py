from __future__ import annotations

import threading

import structlog

from app.core.config import get_settings
from app.models.entities import SttModel
from app.stt.engine import TranscribeOptions, TranscriptionResult
from app.stt.faster_whisper import FasterWhisperEngine

log = structlog.get_logger()


class EngineRegistry:
    """One resident Whisper model per worker process."""

    def __init__(self) -> None:
        self._engines: dict[str, FasterWhisperEngine] = {}
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()

    def loaded_models(self) -> list[str]:
        return sorted(self._engines)

    def warmup(self, model: SttModel, device: str) -> None:
        self._get_or_load(model, device)

    def transcribe(
        self,
        model: SttModel,
        device: str,
        audio_path: str,
        options: TranscribeOptions,
        on_progress=None,
    ) -> TranscriptionResult:
        engine = self._get_or_load(model, device)
        with self._infer_lock:
            return engine.transcribe(audio_path, options, on_progress=on_progress)

    def _get_or_load(self, model: SttModel, device: str) -> FasterWhisperEngine:
        with self._load_lock:
            existing = self._engines.get(model.name)
            if existing is not None:
                return existing
            self._make_room(model)
            compute_type = model.compute_type or get_settings().compute_type
            engine = FasterWhisperEngine(
                model_id=model.whisper_model_id,
                device=device,
                compute_type=compute_type,
                download_root=get_settings().whisper_model_dir,
            )
            log.info("model.loading", model=model.name, device=device, compute_type=compute_type)
            engine.load()
            self._engines[model.name] = engine
            log.info("model.loaded", model=model.name, resident=self.loaded_models())
            return engine

    def _make_room(self, model: SttModel) -> None:
        if not self._engines:
            return
        free_mb = _free_vram_mb()
        if free_mb is None:
            self._unload_all()
            return
        if free_mb < model.vram_mb + 512:
            log.warning("model.unload_for_vram", needed_mb=model.vram_mb, free_mb=free_mb)
            self._unload_all()

    def _unload_all(self) -> None:
        self._engines.clear()
        import gc

        gc.collect()


def _free_vram_mb() -> int | None:
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(get_settings().gpu_index)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return int((memory.total - memory.used) / (1024 * 1024))
    except Exception:
        return None


registry = EngineRegistry()
