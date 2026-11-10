"""Runtime configuration, read from environment variables.

On the AlmaLinux server these are set in /etc/imgserver/imgserver.env
(see deploy/imgserver.env.example). Defaults are suitable for local development.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("IMGSERVER_DATA_DIR", _default_data_dir()))
    )
    api_key: str = field(default_factory=lambda: os.environ.get("IMGSERVER_API_KEY", "change-me"))
    max_upload_bytes: int = field(
        default_factory=lambda: int(os.environ.get("IMGSERVER_MAX_UPLOAD_MB", "10")) * 1024 * 1024
    )
    max_text_length: int = field(
        default_factory=lambda: int(os.environ.get("IMGSERVER_MAX_TEXT_LENGTH", "5000"))
    )

    @property
    def backgrounds_dir(self) -> Path:
        return self.data_dir / "backgrounds"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "metadata.db"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.backgrounds_dir, self.uploads_dir):
            d.mkdir(parents=True, exist_ok=True)
