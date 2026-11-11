"""ATTRial image server: FastAPI application.

Run locally:   uvicorn app.main:app --reload       (from the server/ directory)
On the VM:     managed by systemd (deploy/imgserver.service)
"""
from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from . import storage
from .config import Settings
from .db import Database
from .ui import WEB_GUI_HTML

API_VERSION = "1.0.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_dirs()
        db = Database(settings.db_path)
        _import_loose_backgrounds(settings, db)
        _import_loose_uploads(settings, db)
        app.state.settings = settings
        app.state.db = db
        yield
        db.close()

    app = FastAPI(
        title="ATTRial Image Server",
        version=API_VERSION,
        description="Serves background images and accepts text/image uploads.",
        lifespan=lifespan,
    )

    # ---- dependencies ----------------------------------------------------
    def get_db(request: Request) -> Database:
        return request.app.state.db

    def get_settings(request: Request) -> Settings:
        return request.app.state.settings

    def require_admin(
        x_api_key: str | None = Header(default=None),
        cfg: Settings = Depends(get_settings),
    ) -> None:
        if not x_api_key or not secrets.compare_digest(x_api_key, cfg.api_key):
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")

    # ---- serializers -----------------------------------------------------
    def bg_out(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "filename": row["filename"],
            "content_type": row["content_type"],
            "storage_path": f"backgrounds/{row['filename']}",
            "source": row["source"],
            "upload_id": row["upload_id"],
            "created_at": row["created_at"],
            "url": f"/api/backgrounds/{row['id']}",
        }

    def upload_out(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "text": row["text"],
            "has_image": row["filename"] is not None,
            "filename": row["filename"],
            "content_type": row["content_type"],
            "storage_path": f"uploads/{row['filename']}" if row["filename"] else None,
            "image_url": f"/api/uploads/{row['id']}/image" if row["filename"] else None,
            "original_name": row["original_name"],
            "created_at": row["created_at"],
            "is_background": row.get("background_id") is not None,
            "background_id": row.get("background_id"),
        }

    async def read_limited(file: UploadFile, limit: int) -> bytes:
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(status_code=413, detail=f"Image exceeds {limit // (1024 * 1024)} MB limit.")
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded image is empty.")
        return data

    # ---- routes: web gui & health ----------------------------------------
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/ui", response_class=HTMLResponse, tags=["ui"])
    def web_gui() -> HTMLResponse:
        return HTMLResponse(WEB_GUI_HTML)

    @app.get("/api/health", tags=["system"])
    def health(db: Database = Depends(get_db), cfg: Settings = Depends(get_settings)):
        _import_loose_backgrounds(cfg, db)
        _import_loose_uploads(cfg, db)
        bgs = db.list_backgrounds()
        ups = db.list_uploads(200, 0)
        return {
            "status": "ok",
            "version": API_VERSION,
            "backgrounds": len(bgs),
            "uploads": len(ups),
        }

    @app.get("/api/database", tags=["system"])
    def get_database_overview(db: Database = Depends(get_db), cfg: Settings = Depends(get_settings)):
        """Return all SQLite database records (backgrounds + uploads) and unified image options."""
        _import_loose_backgrounds(cfg, db)
        _import_loose_uploads(cfg, db)
        bgs = [bg_out(r) for r in db.list_backgrounds()]
        ups = [upload_out(r) for r in db.list_uploads(200, 0)]

        all_images: list[dict[str, Any]] = []
        for b in bgs:
            all_images.append({
                "option_id": f"bg:{b['id']}",
                "id": b["id"],
                "table": "backgrounds",
                "name": b["name"] or b["filename"],
                "filename": b["filename"],
                "storage_path": b["storage_path"],
                "content_type": b["content_type"],
                "source": b["source"],
                "is_background": True,
                "upload_id": b["upload_id"],
                "text": None,
                "url": b["url"],
                "created_at": b["created_at"],
            })
        for u in ups:
            if u["has_image"] and not u["is_background"]:
                all_images.append({
                    "option_id": f"up:{u['id']}",
                    "id": u["id"],
                    "table": "uploads",
                    "name": u["original_name"] or u["filename"],
                    "filename": u["filename"],
                    "storage_path": u["storage_path"],
                    "content_type": u["content_type"],
                    "source": "upload_only",
                    "is_background": False,
                    "upload_id": u["id"],
                    "text": u["text"],
                    "url": u["image_url"],
                    "created_at": u["created_at"],
                })

        return {
            "db_file": str(cfg.db_path),
            "backgrounds_dir": str(cfg.backgrounds_dir),
            "uploads_dir": str(cfg.uploads_dir),
            "counts": {
                "backgrounds": len(bgs),
                "uploads": len(ups),
                "total_images": len(all_images),
            },
            "backgrounds": bgs,
            "uploads": ups,
            "all_images": all_images,
        }

    # ---- routes: backgrounds ---------------------------------------------
    @app.get("/api/backgrounds", tags=["backgrounds"])
    def list_backgrounds(db: Database = Depends(get_db), cfg: Settings = Depends(get_settings)):
        _import_loose_backgrounds(cfg, db)
        return [bg_out(r) for r in db.list_backgrounds()]

    @app.get("/api/backgrounds/random", tags=["backgrounds"])
    def random_background(db: Database = Depends(get_db), cfg: Settings = Depends(get_settings)):
        row = db.random_background()
        if not row:
            raise HTTPException(status_code=404, detail="No backgrounds available.")
        return FileResponse(
            cfg.backgrounds_dir / row["filename"],
            media_type=row["content_type"],
            headers={"X-Background-Id": row["id"], "Cache-Control": "no-store"},
        )

    @app.get("/api/backgrounds/{background_id}", tags=["backgrounds"])
    def get_background(background_id: str, db: Database = Depends(get_db),
                       cfg: Settings = Depends(get_settings)):
        row = db.get_background(background_id)
        if not row:
            raise HTTPException(status_code=404, detail="Background not found.")
        return FileResponse(cfg.backgrounds_dir / row["filename"], media_type=row["content_type"],
                            headers={"X-Background-Id": row["id"]})

    @app.post("/api/backgrounds", tags=["backgrounds"], status_code=201,
              dependencies=[Depends(require_admin)])
    async def add_background(image: UploadFile = File(...), name: str | None = Form(default=None),
                             db: Database = Depends(get_db), cfg: Settings = Depends(get_settings)):
        data = await read_limited(image, cfg.max_upload_bytes)
        try:
            filename, ctype = storage.save_image(data, cfg.backgrounds_dir)
        except storage.InvalidImageError as e:
            raise HTTPException(status_code=415, detail=str(e))
        return bg_out(db.add_background(filename, ctype, name or image.filename, "admin"))

    @app.delete("/api/backgrounds/{background_id}", tags=["backgrounds"], status_code=204,
                dependencies=[Depends(require_admin)])
    def delete_background(background_id: str, db: Database = Depends(get_db),
                          cfg: Settings = Depends(get_settings)):
        row = db.get_background(background_id)
        if not row:
            raise HTTPException(status_code=404, detail="Background not found.")
        db.delete_background(background_id)
        storage.delete_file(cfg.backgrounds_dir, row["filename"])  # original upload is kept

    # ---- routes: uploads -------------------------------------------------
    @app.post("/api/uploads", tags=["uploads"], status_code=201)
    async def create_upload(
        text: str | None = Form(default=None),
        image: UploadFile | None = File(default=None),
        add_as_background: bool = Form(default=False),
        db: Database = Depends(get_db),
        cfg: Settings = Depends(get_settings),
    ):
        text = (text or "").strip() or None
        if image is not None and not image.filename:
            image = None  # empty file field sent by some clients
        if text is None and image is None:
            raise HTTPException(status_code=400, detail="Provide text, an image, or both.")
        if text and len(text) > cfg.max_text_length:
            raise HTTPException(status_code=413, detail=f"Text exceeds {cfg.max_text_length} characters.")
        if add_as_background and image is None:
            raise HTTPException(status_code=400, detail="add_as_background requires an image.")

        filename = ctype = original = None
        if image is not None:
            data = await read_limited(image, cfg.max_upload_bytes)
            try:
                filename, ctype = storage.save_image(data, cfg.uploads_dir)
            except storage.InvalidImageError as e:
                raise HTTPException(status_code=415, detail=str(e))
            original = image.filename

        row = db.add_upload(text, filename, ctype, original)
        if add_as_background and filename:
            _promote(row, db, cfg)
            row = db.get_upload(row["id"])
        return upload_out(row)

    @app.get("/api/uploads", tags=["uploads"])
    def list_uploads(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                     db: Database = Depends(get_db), cfg: Settings = Depends(get_settings)):
        _import_loose_uploads(cfg, db)
        return [upload_out(r) for r in db.list_uploads(limit, offset)]

    @app.get("/api/uploads/{upload_id}", tags=["uploads"])
    def get_upload(upload_id: str, db: Database = Depends(get_db)):
        row = db.get_upload(upload_id)
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found.")
        return upload_out(row)

    @app.get("/api/uploads/{upload_id}/image", tags=["uploads"])
    def get_upload_image(upload_id: str, db: Database = Depends(get_db),
                         cfg: Settings = Depends(get_settings)):
        row = db.get_upload(upload_id)
        if not row or not row["filename"]:
            raise HTTPException(status_code=404, detail="Upload image not found.")
        return FileResponse(cfg.uploads_dir / row["filename"], media_type=row["content_type"])

    @app.post("/api/uploads/{upload_id}/promote", tags=["uploads"])
    def promote_upload(upload_id: str, db: Database = Depends(get_db),
                       cfg: Settings = Depends(get_settings)):
        row = db.get_upload(upload_id)
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found.")
        if not row["filename"]:
            raise HTTPException(status_code=400, detail="This upload has no image.")
        existing = db.background_for_upload(upload_id)
        if existing:
            return bg_out(existing)  # idempotent
        return bg_out(_promote(row, db, cfg))

    @app.delete("/api/uploads/{upload_id}", tags=["uploads"], status_code=204,
                dependencies=[Depends(require_admin)])
    def delete_upload(upload_id: str, db: Database = Depends(get_db),
                      cfg: Settings = Depends(get_settings)):
        row = db.get_upload(upload_id)
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found.")
        db.delete_upload(upload_id)
        storage.delete_file(cfg.uploads_dir, row["filename"])  # promoted background copy is kept

    return app


def _promote(upload_row: dict[str, Any], db: Database, cfg: Settings) -> dict[str, Any]:
    new_name = storage.copy_image(cfg.uploads_dir, upload_row["filename"], cfg.backgrounds_dir)
    return db.add_background(new_name, upload_row["content_type"], upload_row["original_name"],
                             "upload", upload_row["id"])


def _import_loose_backgrounds(cfg: Settings, db: Database) -> None:
    """Register image files copied straight into the backgrounds folder (e.g. via scp)."""
    known = db.background_filenames()
    for path in sorted(cfg.backgrounds_dir.iterdir()):
        if not path.is_file() or path.name in known:
            continue
        try:
            with path.open("rb") as f:
                _, ctype = storage.detect_image_type(f.read(16))
        except storage.InvalidImageError:
            continue
        db.add_background(path.name, ctype, path.name, "admin")


def _import_loose_uploads(cfg: Settings, db: Database) -> None:
    """Register image files copied straight into the uploads folder so they appear in the DB."""
    known = db.upload_filenames()
    for path in sorted(cfg.uploads_dir.iterdir()):
        if not path.is_file() or path.name in known:
            continue
        try:
            with path.open("rb") as f:
                _, ctype = storage.detect_image_type(f.read(16))
        except storage.InvalidImageError:
            continue
        db.add_upload(None, path.name, ctype, path.name)


app = create_app()
