import io

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
API_KEY = "test-key"


@pytest.fixture()
def client(tmp_path):
    # A "loose" file dropped into the backgrounds folder should be auto-imported.
    (tmp_path / "backgrounds").mkdir()
    (tmp_path / "backgrounds" / "seed.png").write_bytes(PNG)
    settings = Settings(data_dir=tmp_path, api_key=API_KEY, max_upload_bytes=1024, max_text_length=50)
    with TestClient(create_app(settings)) as c:
        yield c


def img(data=PNG, name="pic.png"):
    return {"image": (name, io.BytesIO(data), "image/png")}


def test_health_and_seeded_background(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["backgrounds"] == 1
    bgs = client.get("/api/backgrounds").json()
    assert len(bgs) == 1
    r = client.get("/api/backgrounds/random")
    assert r.status_code == 200 and r.content == PNG
    assert r.headers["x-background-id"] == bgs[0]["id"]


def test_text_only_upload(client):
    r = client.post("/api/uploads", data={"text": "hello"})
    assert r.status_code == 201
    body = r.json()
    assert body["text"] == "hello" and body["has_image"] is False and body["is_background"] is False


def test_image_upload_kept_separate(client):
    r = client.post("/api/uploads", data={"text": "cat"}, files=img(JPEG, "cat.jpg"))
    assert r.status_code == 201
    up = r.json()
    assert up["is_background"] is False
    assert client.get(up["image_url"]).content == JPEG
    assert len(client.get("/api/backgrounds").json()) == 1


def test_image_upload_added_as_background(client):
    r = client.post("/api/uploads", data={"add_as_background": "true"}, files=img())
    up = r.json()
    assert r.status_code == 201 and up["is_background"] is True
    bgs = client.get("/api/backgrounds").json()
    assert len(bgs) == 2
    assert any(b["source"] == "upload" and b["upload_id"] == up["id"] for b in bgs)


def test_promote_later_is_idempotent(client):
    up = client.post("/api/uploads", files=img()).json()
    first = client.post(f"/api/uploads/{up['id']}/promote")
    second = client.post(f"/api/uploads/{up['id']}/promote")
    assert first.status_code == 200 and first.json()["id"] == second.json()["id"]
    assert client.get(f"/api/uploads/{up['id']}").json()["is_background"] is True
    assert len(client.get("/api/backgrounds").json()) == 2


def test_validation_errors(client):
    assert client.post("/api/uploads", data={"text": "  "}).status_code == 400
    assert client.post("/api/uploads", data={"text": "x" * 51}).status_code == 413
    assert client.post("/api/uploads", files=img(b"not an image")).status_code == 415
    assert client.post("/api/uploads", files=img(PNG + b"\x00" * 2000)).status_code == 413
    assert client.post("/api/uploads", data={"text": "a", "add_as_background": "true"}).status_code == 400
    text_up = client.post("/api/uploads", data={"text": "a"}).json()
    assert client.post(f"/api/uploads/{text_up['id']}/promote").status_code == 400


def test_admin_endpoints_require_key(client):
    assert client.post("/api/backgrounds", files=img()).status_code == 401
    r = client.post("/api/backgrounds", files=img(), headers={"X-API-Key": API_KEY})
    assert r.status_code == 201
    bid = r.json()["id"]
    assert client.delete(f"/api/backgrounds/{bid}").status_code == 401
    assert client.delete(f"/api/backgrounds/{bid}", headers={"X-API-Key": API_KEY}).status_code == 204
    assert client.get(f"/api/backgrounds/{bid}").status_code == 404


def test_delete_upload_keeps_promoted_background(client):
    up = client.post("/api/uploads", data={"add_as_background": "true"}, files=img()).json()
    assert client.delete(f"/api/uploads/{up['id']}", headers={"X-API-Key": API_KEY}).status_code == 204
    assert client.get(f"/api/uploads/{up['id']}").status_code == 404
    bg = up["background_id"]
    assert client.get(f"/api/backgrounds/{bg}").status_code == 200
