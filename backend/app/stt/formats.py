from __future__ import annotations


def _ts(seconds: float, separator: str) -> str:
    if seconds < 0:
        seconds = 0
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def _clean(text: str) -> str:
    return " ".join((text or "").replace("\r", " ").replace("\n", " ").split())


def segments_to_srt(segments: list[dict]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = _ts(float(segment["start"]), ",")
        end = _ts(float(segment["end"]), ",")
        blocks.append(f"{index}\n{start} --> {end}\n{_clean(segment.get('text', ''))}\n")
    return "\n".join(blocks).strip() + ("\n" if blocks else "")


def segments_to_vtt(segments: list[dict]) -> str:
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = _ts(float(segment["start"]), ".")
        end = _ts(float(segment["end"]), ".")
        lines.append(f"{start} --> {end}")
        lines.append(_clean(segment.get("text", "")))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def segments_to_text(segments: list[dict]) -> str:
    return " ".join(_clean(segment.get("text", "")) for segment in segments if _clean(segment.get("text", ""))).strip()
