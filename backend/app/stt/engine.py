from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


@dataclass
class TranscribeOptions:
    language: str | None = None
    task: str = "transcribe"
    beam_size: int = 5
    temperature: float = 0.0
    vad_filter: bool = True
    word_timestamps: bool = True
    initial_prompt: str | None = None


@dataclass
class TranscriptionResult:
    text: str
    language: str | None
    duration: float | None
    segments: list[dict] = field(default_factory=list)


class STTEngine(Protocol):
    def load(self) -> None: ...

    def transcribe(
        self,
        audio_path: str,
        options: TranscribeOptions,
        on_progress: Callable[[float], None] | None = None,
    ) -> TranscriptionResult: ...
