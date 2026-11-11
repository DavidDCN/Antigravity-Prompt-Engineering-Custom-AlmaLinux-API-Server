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


def test_web_gui_served_at_root_and_ui(client):
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "text/html" in r_root.headers["content-type"]
    assert "ATTRial AlmaLinux Image" in r_root.text
    assert "Open Background Viewer Frame" in r_root.text
    r_ui = client.get("/ui")
    assert r_ui.status_code == 200
    assert "Alma Server Backgrounds Gallery" in r_ui.text


def test_database_overview_and_loose_files(client):
    # Upload one separate image so we have 1 background + 1 upload-only image
    up = client.post("/api/uploads", data={"text": "note"}, files=img(JPEG, "only_upload.jpg")).json()
    db_info = client.get("/api/database").json()
    assert db_info["counts"]["backgrounds"] == 1
    assert db_info["counts"]["uploads"] == 1
    assert db_info["counts"]["total_images"] == 2
    option_ids = {item["option_id"] for item in db_info["all_images"]}
    assert f"up:{up['id']}" in option_ids


def test_two_way_mirror_dir_sync(tmp_path):
    data_dir = tmp_path / "data"
    mirror_dir = tmp_path / "Downloads" / "background images"
    mirror_dir.mkdir(parents=True)
    # 1. Put 1.jpg and 2.jpeg inside the AlmaLinux mirror folder
    (mirror_dir / "1.jpg").write_bytes(JPEG)
    (mirror_dir / "2.jpeg").write_bytes(JPEG)

    settings = Settings(data_dir=data_dir, mirror_dir=mirror_dir, api_key=API_KEY)
    with TestClient(create_app(settings)) as c:
        bgs = c.get("/api/backgrounds").json()
        names = {b["name"] for b in bgs}
        assert "1.jpg" in names and "2.jpeg" in names

        # 2. Upload wifi.png via API -> should appear inside mirror_dir as wifi.png
        r = c.post("/api/uploads", data={"add_as_background": "true"}, files=img(PNG, "wifi.png"))
        assert r.status_code == 201
        assert (mirror_dir / "wifi.png").is_file()
        assert (mirror_dir / "wifi.png").read_bytes() == PNG


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
