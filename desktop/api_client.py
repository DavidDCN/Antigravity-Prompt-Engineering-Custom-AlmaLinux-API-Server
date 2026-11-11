"""Thin HTTP client for the ATTRial image server API."""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


class ApiError(Exception):
    pass


@dataclass
class ApiClient:
    base_url: str
    timeout: float = 15.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.strip().rstrip("/")
        if self.base_url and "://" not in self.base_url:
            self.base_url = "http://" + self.base_url
        self._session = requests.Session()

    def url(self, path: str) -> str:
        return self.base_url + path

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        try:
            r = self._session.request(method, self.url(path), timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise ApiError(f"Cannot reach server at {self.base_url}: {e.__class__.__name__}") from e
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ApiError(f"Server error {r.status_code}: {detail}")
        return r

    # ---- endpoints -------------------------------------------------------
    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/health").json()

    def list_backgrounds(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/backgrounds").json()

    def random_background(self) -> tuple[bytes, str | None]:
        r = self._request("GET", "/api/backgrounds/random")
        return r.content, r.headers.get("X-Background-Id")

    def list_uploads(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._request("GET", "/api/uploads", params={"limit": limit}).json()

    def get_bytes(self, path: str) -> bytes:
        return self._request("GET", path).content

    def upload(self, text: str | None, image_path: str | None, add_as_background: bool) -> dict[str, Any]:
        data = {"add_as_background": "true" if add_as_background else "false"}
        if text:
            data["text"] = text
        files = None
        fh = None
        try:
            if image_path:
                p = Path(image_path)
                ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                fh = p.open("rb")
                files = {"image": (p.name, fh, ctype)}
            return self._request("POST", "/api/uploads", data=data, files=files).json()
        finally:
            if fh:
                fh.close()

    def promote(self, upload_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/uploads/{upload_id}/promote").json()
