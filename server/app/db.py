"""SQLite metadata store for backgrounds and uploads."""
from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    id            TEXT PRIMARY KEY,
    text          TEXT,
    filename      TEXT,
    content_type  TEXT,
    original_name TEXT,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS backgrounds (
    id            TEXT PRIMARY KEY,
    filename      TEXT NOT NULL,
    content_type  TEXT NOT NULL,
    name          TEXT,
    source        TEXT NOT NULL CHECK (source IN ('admin', 'upload')),
    upload_id     TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_backgrounds_upload ON backgrounds(upload_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _exec(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            self._conn.commit()
            return rows

    # ---- uploads -------------------------------------------------------
    def add_upload(self, text: str | None, filename: str | None, content_type: str | None,
                   original_name: str | None) -> dict[str, Any]:
        uid = uuid.uuid4().hex
        self._exec(
            "INSERT INTO uploads (id, text, filename, content_type, original_name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uid, text, filename, content_type, original_name, _now()),
        )
        return self.get_upload(uid)  # type: ignore[return-value]

    _UPLOAD_SELECT = (
        "SELECT u.*, (SELECT b.id FROM backgrounds b WHERE b.upload_id = u.id LIMIT 1) "
        "AS background_id FROM uploads u"
    )

    def get_upload(self, uid: str) -> dict[str, Any] | None:
        rows = self._exec(f"{self._UPLOAD_SELECT} WHERE u.id = ?", (uid,))
        return rows[0] if rows else None

    def list_uploads(self, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._exec(
            f"{self._UPLOAD_SELECT} ORDER BY u.created_at DESC, u.rowid DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def delete_upload(self, uid: str) -> None:
        self._exec("DELETE FROM uploads WHERE id = ?", (uid,))

    def upload_filenames(self) -> set[str]:
        return {
            r["filename"]
            for r in self._exec("SELECT filename FROM uploads WHERE filename IS NOT NULL")
        }

    # ---- backgrounds ---------------------------------------------------
    def add_background(self, filename: str, content_type: str, name: str | None,
                       source: str, upload_id: str | None = None) -> dict[str, Any]:
        bid = uuid.uuid4().hex
        self._exec(
            "INSERT INTO backgrounds (id, filename, content_type, name, source, upload_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (bid, filename, content_type, name, source, upload_id, _now()),
        )
        return self.get_background(bid)  # type: ignore[return-value]

    def get_background(self, bid: str) -> dict[str, Any] | None:
        rows = self._exec("SELECT * FROM backgrounds WHERE id = ?", (bid,))
        return rows[0] if rows else None

    def list_backgrounds(self) -> list[dict[str, Any]]:
        return self._exec("SELECT * FROM backgrounds ORDER BY created_at, rowid")

    def random_background(self) -> dict[str, Any] | None:
        rows = self._exec("SELECT * FROM backgrounds ORDER BY RANDOM() LIMIT 1")
        return rows[0] if rows else None

    def background_for_upload(self, upload_id: str) -> dict[str, Any] | None:
        rows = self._exec("SELECT * FROM backgrounds WHERE upload_id = ? LIMIT 1", (upload_id,))
        return rows[0] if rows else None

    def background_filenames(self) -> set[str]:
        return {r["filename"] for r in self._exec("SELECT filename FROM backgrounds")}

    def delete_background(self, bid: str) -> None:
        self._exec("DELETE FROM backgrounds WHERE id = ?", (bid,))
