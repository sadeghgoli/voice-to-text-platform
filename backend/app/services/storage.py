from __future__ import annotations

from pathlib import Path

import filetype

from app.core.errors import AppError
from app.services.validators import ensure_allowed_mime, safe_path


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def original_path(self, job_id: str, ext: str) -> Path:
        if not ext.startswith(".") or "/" in ext or "\\" in ext:
            raise AppError("validation_error", "پسوند فایل نامعتبر است.", 400)
        folder = safe_path(self.root, "uploads", job_id)
        folder.mkdir(parents=True, exist_ok=True)
        return safe_path(self.root, "uploads", job_id, f"original{ext}")

    def normalized_path(self, job_id: str) -> Path:
        folder = safe_path(self.root, "normalized")
        folder.mkdir(parents=True, exist_ok=True)
        return safe_path(self.root, "normalized", f"{job_id}.wav")

    def delete_file(self, path: str | None) -> None:
        if not path:
            return
        candidate = Path(path).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            return
        if candidate.is_file():
            candidate.unlink()


def sniff_mime(path: Path) -> str | None:
    kind = filetype.guess(str(path))
    if kind is None:
        return None
    return kind.mime


def assert_mime(path: Path, ext: str) -> str:
    return ensure_allowed_mime(ext, sniff_mime(path))
