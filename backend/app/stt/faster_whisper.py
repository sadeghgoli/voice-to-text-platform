from __future__ import annotations

import structlog

from app.stt.engine import TranscribeOptions, TranscriptionResult

log = structlog.get_logger()


class FasterWhisperEngine:
    def __init__(self, model_id: str, device: str, compute_type: str, download_root: str) -> None:
        self.model_id = model_id
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self._model = None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        compute_type = self.compute_type
        if self.device == "cpu" and compute_type in {"float16", "int8_float16"}:
            compute_type = "int8"
        try:
            self._model = WhisperModel(
                self.model_id,
                device=self.device,
                compute_type=compute_type,
                download_root=self.download_root,
            )
        except Exception as exc:
            log.error("model.load_failed", model=self.model_id, device=self.device, error=str(exc))
            raise

    def transcribe(
        self,
        audio_path: str,
        options: TranscribeOptions,
        on_progress=None,
    ) -> TranscriptionResult:
        if self._model is None:
            raise RuntimeError("مدل هنوز بارگذاری نشده است.")
        language = None if options.language in {None, "", "auto"} else options.language
        try:
            segments_iter, info = self._model.transcribe(
                audio_path,
                language=language,
                task=options.task,
                beam_size=options.beam_size,
                temperature=options.temperature,
                vad_filter=options.vad_filter,
                word_timestamps=options.word_timestamps,
                initial_prompt=options.initial_prompt or None,
            )
        except Exception as exc:
            log.error("transcription.failed", model=self.model_id, error=str(exc))
            raise
        segments: list[dict] = []
        for segment in segments_iter:
            words = None
            if options.word_timestamps and getattr(segment, "words", None):
                words = [
                    {
                        "start": round(word.start, 3),
                        "end": round(word.end, 3),
                        "word": word.word,
                        "probability": round(float(word.probability), 4),
                    }
                    for word in segment.words
                ]
            item = {
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": (segment.text or "").strip(),
                "words": words,
            }
            segments.append(item)
            if on_progress is not None:
                on_progress(float(segment.end))
        text = " ".join(item["text"] for item in segments if item["text"]).strip()
        detected = getattr(info, "language", None)
        duration = getattr(info, "duration", None)
        return TranscriptionResult(text=text, language=detected, duration=duration, segments=segments)
