"""Image validation and file storage helpers."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

# Magic-byte signatures -> (extension, content type). We check the real bytes
# instead of trusting the client-supplied filename or Content-Type header.
_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
)


class InvalidImageError(ValueError):
    pass


def detect_image_type(data: bytes) -> tuple[str, str]:
    """Return (extension, content_type) for JPEG/PNG/WebP, else raise."""
    for sig, ext, ctype in _SIGNATURES:
        if data.startswith(sig):
            return ext, ctype
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    raise InvalidImageError("Only JPEG, PNG and WebP images are allowed.")


def save_image(data: bytes, directory: Path) -> tuple[str, str]:
    """Validate and save image bytes under a random name. Returns (filename, content_type)."""
    ext, ctype = detect_image_type(data)
    filename = f"{uuid.uuid4().hex}{ext}"
    (directory / filename).write_bytes(data)
    return filename, ctype


def copy_image(src_dir: Path, filename: str, dst_dir: Path) -> str:
    """Copy an existing stored image into another directory under a new random name."""
    new_name = f"{uuid.uuid4().hex}{Path(filename).suffix}"
    shutil.copyfile(src_dir / filename, dst_dir / new_name)
    return new_name


def delete_file(directory: Path, filename: str | None) -> None:
    if filename:
        (directory / filename).unlink(missing_ok=True)
