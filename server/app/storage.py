"""Image validation and file storage helpers."""
from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

# Magic-byte signatures -> (extension, content type). We check the real bytes
# instead of trusting the client-supplied filename or Content-Type header.
_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"GIF87a", ".gif", "image/gif"),
    (b"GIF89a", ".gif", "image/gif"),
    (b"BM", ".bmp", "image/bmp"),
)


class InvalidImageError(ValueError):
    pass


def detect_image_type(data: bytes) -> tuple[str, str]:
    """Return (extension, content_type) for supported image formats, else raise."""
    for sig, ext, ctype in _SIGNATURES:
        if data.startswith(sig):
            return ext, ctype
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis", b"mif1"):
        return ".avif", "image/avif"
    raise InvalidImageError("Only JPEG, PNG, WebP, AVIF, GIF and BMP images are allowed.")


def safe_visible_filename(original_name: str | None, fallback_ext: str = ".png") -> str:
    """Sanitize a filename so it can be safely mirrored into the user's visible folder."""
    raw = Path(original_name or f"image{fallback_ext}").name
    clean = re.sub(r"[^A-Za-z0-9._ -]", "_", raw).strip(" .")
    if not clean:
        clean = f"image{fallback_ext}"
    if "." not in clean:
        clean += fallback_ext
    return clean


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
