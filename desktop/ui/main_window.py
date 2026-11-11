"""Main window of the ATTRial desktop client."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from api_client import ApiClient
from ui.background import BackgroundFrame
from ui.worker import TaskRunner

ROTATE_MS = 60_000
MAX_TEXT = 5000

STYLE = """
QWidget#root { background: #0b0f19; }
QFrame#panel { background: #111827; border: 1px solid #334155; border-radius: 12px; }
QLabel, QCheckBox { color: #f0f0f0; }
QLabel#title { font-size: 15px; font-weight: 600; }
QLabel#guide {
    background: rgba(37, 99, 235, 65);
    border: 1px solid rgba(96, 165, 250, 120);
    border-radius: 8px;
    padding: 8px;
    color: #e2e8f0;
    font-size: 12px;
}
QLabel#status { color: #cfd8dc; }
QLineEdit, QPlainTextEdit, QListWidget {
    background: rgba(255, 255, 255, 235); color: #111; border-radius: 6px; padding: 4px;
}
QPushButton {
    background: #3f6fd8; color: white; border: none; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background: #5583ea; }
QPushButton:disabled { background: #6b7280; color: #d1d5db; }
QLabel#preview { background: rgba(255,255,255,40); border-radius: 6px; color: #bbb; }
"""


def panel() -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("panel")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(14, 12, 14, 12)
    return f, lay


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ATTRial Client")
        self.resize(1240, 760)
        self.settings = QSettings("ATTRial", "Client")
        self.tasks = TaskRunner()
        self.api: ApiClient | None = None
        self.image_path: str | None = None

        central = QWidget()
        central.setObjectName("root")
        central.setStyleSheet(STYLE)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # --- connection bar ---
        bar, bar_l = panel()
        row = QHBoxLayout()
        bar_l.addLayout(row)
        row.addWidget(QLabel("Alma Server URL:"))
        self.url_edit = QLineEdit(self.settings.value("server_url", "http://192.168.1.11"))
        self.url_edit.setPlaceholderText("http://<server-ip>")
        self.url_edit.returnPressed.connect(self.connect_server)
        row.addWidget(self.url_edit, 1)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_server)
        row.addWidget(self.connect_btn)
        self.next_bg_btn = QPushButton("🎲 Random Background")
        self.next_bg_btn.clicked.connect(self.load_background)
        row.addWidget(self.next_bg_btn)
        self.web_gui_btn = QPushButton("🌐 Open Web GUI")
        self.web_gui_btn.clicked.connect(self.open_web_gui)
        row.addWidget(self.web_gui_btn)
        self.status = QLabel("Not connected — enter your AlmaLinux VM IP (e.g. http://192.168.1.11) and click Connect.")
        self.status.setObjectName("status")
        bar_l.addWidget(self.status)
        root.addWidget(bar)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # --- upload panel ---
        up, up_l = panel()
        t = QLabel("Step-by-Step: Upload Image or Text")
        t.setObjectName("title")
        up_l.addWidget(t)
        guide_lbl = QLabel(
            "1. Type a text note, choose an image (JPEG/PNG/WebP), or both.\n"
            "2. Optional: Tick 'Also use this image as a background'.\n"
            "3. Click Upload (POST /api/uploads → Nginx :80 → FastAPI :8000)."
        )
        guide_lbl.setObjectName("guide")
        guide_lbl.setWordWrap(True)
        up_l.addWidget(guide_lbl)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(f"Step 1a: Write some text (optional, max {MAX_TEXT} characters)…")
        up_l.addWidget(self.text_edit, 1)
        img_row = QHBoxLayout()
        self.choose_btn = QPushButton("Step 1b: Choose image…")
        self.choose_btn.clicked.connect(self.choose_image)
        self.clear_img_btn = QPushButton("Remove image")
        self.clear_img_btn.clicked.connect(self.clear_image)
        img_row.addWidget(self.choose_btn)
        img_row.addWidget(self.clear_img_btn)
        img_row.addStretch(1)
        up_l.addLayout(img_row)
        self.preview = QLabel("No image selected")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedHeight(140)
        up_l.addWidget(self.preview)
        self.as_bg_check = QCheckBox("Step 2: Also use this image as an Alma Server background")
        up_l.addWidget(self.as_bg_check)
        self.upload_btn = QPushButton("Step 3: ⬆ Upload to Alma Server")
        self.upload_btn.clicked.connect(self.do_upload)
        up_l.addWidget(self.upload_btn)
        body.addWidget(up, 1)

        # --- dedicated open background viewer frame + scrollable options ---
        stage_pnl, stage_l = panel()
        t_stage = QLabel("Open Background Viewer Frame")
        t_stage.setObjectName("title")
        stage_l.addWidget(t_stage)
        self.frame_info = QLabel("Dedicated open space to view backgrounds and uploaded images clearly.")
        self.frame_info.setWordWrap(True)
        stage_l.addWidget(self.frame_info)

        self.bg = BackgroundFrame(fit_mode=True)
        self.bg.setMinimumHeight(260)
        stage_l.addWidget(self.bg, 2)

        stage_btns = QHBoxLayout()
        self.prev_opt_btn = QPushButton("◀ Prev")
        self.prev_opt_btn.clicked.connect(lambda: self.step_bg_option(-1))
        self.next_opt_btn = QPushButton("Next ▶")
        self.next_opt_btn.clicked.connect(lambda: self.step_bg_option(1))
        self.fit_btn = QPushButton("📐 Fit / Fill")
        self.fit_btn.clicked.connect(self.toggle_frame_fit)
        self.refresh_bg_btn = QPushButton("↻ Refresh Options")
        self.refresh_bg_btn.clicked.connect(self.load_backgrounds_gallery)
        stage_btns.addWidget(self.prev_opt_btn)
        stage_btns.addWidget(self.next_opt_btn)
        stage_btns.addWidget(self.fit_btn)
        stage_btns.addWidget(self.refresh_bg_btn)
        stage_l.addLayout(stage_btns)

        bg_hint = QLabel("Scroll all Server Backgrounds (click any to view in the open frame above):")
        bg_hint.setWordWrap(True)
        stage_l.addWidget(bg_hint)
        self.bg_list = QListWidget()
        self.bg_list.setIconSize(QSize(64, 64))
        self.bg_list.setWordWrap(True)
        self.bg_list.currentItemChanged.connect(self.apply_selected_background)
        stage_l.addWidget(self.bg_list, 1)
        body.addWidget(stage_pnl, 2)

        # --- uploads list panel ---
        lst, lst_l = panel()
        t2 = QLabel("All Database Uploads (Images & Text)")
        t2.setObjectName("title")
        lst_l.addWidget(t2)
        up_hint = QLabel("Scroll records in /srv/imgserver/data/uploads/ (click an image upload to preview in frame):")
        up_hint.setWordWrap(True)
        lst_l.addWidget(up_hint)
        self.list = QListWidget()
        self.list.setIconSize(QSize(64, 64))
        self.list.setWordWrap(True)
        self.list.currentItemChanged.connect(self._on_upload_selected)
        lst_l.addWidget(self.list, 1)
        lrow = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Uploads")
        self.refresh_btn.clicked.connect(self.load_uploads)
        self.promote_btn = QPushButton("★ Promote to Background")
        self.promote_btn.clicked.connect(self.promote_selected)
        lrow.addWidget(self.refresh_btn)
        lrow.addWidget(self.promote_btn)
        lrow.addStretch(1)
        lst_l.addLayout(lrow)
        body.addWidget(lst, 1)

        self.rotate_timer = QTimer(self)
        self.rotate_timer.setInterval(ROTATE_MS)
        self.rotate_timer.timeout.connect(self.load_background)

        self._set_connected(False)
        self.clear_image()
        if self.settings.value("server_url"):
            QTimer.singleShot(0, self.connect_server)

    # ---------------------------------------------------------------- helpers
    def _set_connected(self, ok: bool) -> None:
        for w in (self.next_bg_btn, self.upload_btn, self.refresh_btn, self.refresh_bg_btn,
                  self.prev_opt_btn, self.next_opt_btn, self.fit_btn,
                  self.choose_btn, self.text_edit, self.as_bg_check):
            w.setEnabled(ok)
        self._update_buttons()
        if ok:
            self.rotate_timer.start()
        else:
            self.rotate_timer.stop()

    def open_web_gui(self) -> None:
        url = self.url_edit.text().strip().rstrip("/")
        if url and "://" not in url:
            url = "http://" + url
        if url:
            QDesktopServices.openUrl(QUrl(url + "/"))

    def toggle_frame_fit(self) -> None:
        is_fit = self.bg.toggle_fit_mode()
        self.status.setText("📐 Open Frame Mode: Fit Whole Image" if is_fit else "📐 Open Frame Mode: Fill Frame")

    def step_bg_option(self, delta: int) -> None:
        count = self.bg_list.count()
        if count == 0:
            return
        idx = self.bg_list.currentRow()
        next_idx = 0 if idx < 0 else (idx + delta) % count
        self.bg_list.setCurrentRow(next_idx)

    def _on_upload_selected(self, current: QListWidgetItem | None, *_):
        self._update_buttons()
        if not current:
            return
        payload = current.data(Qt.UserRole)
        if isinstance(payload, dict):
            raw = current.data(Qt.UserRole + 1)
            if raw and self.bg.set_image(raw):
                name = payload.get("original_name") or payload["id"][:10]
                self.frame_info.setText(f"Viewing Upload in Open Frame: {name} (/api/uploads/{payload['id']}/image)")

    def _update_buttons(self, *_):
        item = self.list.currentItem()
        data = item.data(Qt.UserRole) if item else None
        self.promote_btn.setEnabled(
            self.api is not None and bool(data) and data["has_image"] and not data["is_background"]
        )
        self.clear_img_btn.setEnabled(self.image_path is not None)
        self.as_bg_check.setEnabled(self.api is not None and self.image_path is not None)

    def _error(self, msg: str) -> None:
        self.status.setText(f"⚠ {msg}")

    # ------------------------------------------------------------- connection
    def connect_server(self) -> None:
        api = ApiClient(self.url_edit.text())
        if not api.base_url:
            self._error("Enter the server address first.")
            return
        self.url_edit.setText(api.base_url)
        self.status.setText(f"Connecting to {api.base_url}…")
        self.connect_btn.setEnabled(False)

        def ok(info):
            self.api = api
            self.settings.setValue("server_url", api.base_url)
            self.connect_btn.setEnabled(True)
            self.status.setText(
                f"✔ Connected to {api.base_url} (API v{info['version']}, {info['backgrounds']} backgrounds)"
            )
            self._set_connected(True)
            self.load_background()
            self.load_backgrounds_gallery()
            self.load_uploads()

        def fail(msg):
            self.api = None
            self.connect_btn.setEnabled(True)
            self._set_connected(False)
            self._error(msg)

        self.tasks.run(api.health, ok, fail)

    # ------------------------------------------------------------ backgrounds
    def load_background(self) -> None:
        if not self.api:
            return
        api = self.api

        def ok(result):
            data, bid = result
            if not self.bg.set_image(data):
                self._error("Server sent an image that could not be displayed.")
            else:
                self.frame_info.setText(f"Viewing Server Background ID: {bid or 'random'}")

        def fail(msg):
            if "404" in msg:
                self.status.setText("Connected, but the server has no backgrounds yet.")
            else:
                self._error(msg)

        self.tasks.run(api.random_background, ok, fail)

    def load_backgrounds_gallery(self) -> None:
        if not self.api:
            return
        api = self.api

        def fetch():
            items = api.list_backgrounds()
            thumbs = {}
            for it in items:
                try:
                    thumbs[it["id"]] = api.get_bytes(it["url"])
                except Exception:  # noqa: BLE001
                    pass
            return items, thumbs

        def ok(result):
            items, thumbs = result
            self.bg_list.clear()
            for it in items:
                when = it["created_at"]
                try:
                    when = datetime.fromisoformat(when).astimezone().strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
                src = "Admin / Server" if it["source"] == "admin" else "★ Promoted Upload"
                name = it["name"] or it["id"][:10]
                item = QListWidgetItem(f"{name}\n[{src}] {when}")
                item.setData(Qt.UserRole, (it, thumbs.get(it["id"])))
                if it["id"] in thumbs:
                    pm = QPixmap()
                    if pm.loadFromData(thumbs[it["id"]]):
                        item.setIcon(QIcon(pm))
                self.bg_list.addItem(item)

        self.tasks.run(fetch, ok, self._error)

    def apply_selected_background(self, item: QListWidgetItem | None, *_) -> None:
        if not item:
            return
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        it, raw_bytes = payload
        if raw_bytes and self.bg.set_image(raw_bytes):
            name = it.get("name") or it["id"]
            self.frame_info.setText(f"Viewing Background in Open Frame: {name} ({it.get('url', '')})")
            self.status.setText(f"✔ Displaying background in open frame: {name}")

    # ---------------------------------------------------------------- uploads
    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose image", "",
                                              "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        pm = QPixmap(path)
        if pm.isNull():
            QMessageBox.warning(self, "Invalid image", "That file could not be opened as an image.")
            return
        self.image_path = path
        self.preview.setPixmap(pm.scaled(self.preview.width() - 8, self.preview.height() - 8,
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.preview.setToolTip(path)
        self._update_buttons()

    def clear_image(self) -> None:
        self.image_path = None
        self.preview.clear()
        self.preview.setText("No image selected")
        self.as_bg_check.setChecked(False)
        self._update_buttons()

    def do_upload(self) -> None:
        if not self.api:
            return
        text = self.text_edit.toPlainText().strip()
        if not text and not self.image_path:
            self._error("Write some text or choose an image to upload.")
            return
        if len(text) > MAX_TEXT:
            self._error(f"Text is too long ({len(text)}/{MAX_TEXT}).")
            return
        api, path, as_bg = self.api, self.image_path, self.as_bg_check.isChecked()
        self.upload_btn.setEnabled(False)
        self.status.setText("Uploading…")

        def ok(result):
            self.upload_btn.setEnabled(True)
            self.text_edit.clear()
            self.clear_image()
            extra = " and added as background" if result.get("is_background") else ""
            self.status.setText(f"✔ Uploaded{extra}.")
            self.load_uploads()
            if result.get("is_background"):
                self.load_backgrounds_gallery()

        def fail(msg):
            self.upload_btn.setEnabled(True)
            self._error(msg)

        self.tasks.run(lambda: api.upload(text or None, path, as_bg), ok, fail)

    def load_uploads(self) -> None:
        if not self.api:
            return
        api = self.api

        def fetch():
            items = api.list_uploads()
            thumbs = {}
            for it in items:
                if it["image_url"]:
                    try:
                        thumbs[it["id"]] = api.get_bytes(it["image_url"])
                    except Exception:  # noqa: BLE001 - a missing thumbnail is not fatal
                        pass
            return items, thumbs

        def ok(result):
            items, thumbs = result
            self.list.clear()
            for it in items:
                when = it["created_at"]
                try:
                    when = datetime.fromisoformat(when).astimezone().strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
                label = it["text"] or f"[image] {it['original_name'] or ''}"
                if len(label) > 140:
                    label = label[:140] + "…"
                tag = "  ★ background" if it["is_background"] else ""
                item = QListWidgetItem(f"{label}\n{when}{tag}")
                item.setData(Qt.UserRole, it)
                if it["id"] in thumbs:
                    item.setData(Qt.UserRole + 1, thumbs[it["id"]])
                    pm = QPixmap()
                    if pm.loadFromData(thumbs[it["id"]]):
                        item.setIcon(QIcon(pm))
                self.list.addItem(item)
            self._update_buttons()

        self.tasks.run(fetch, ok, self._error)

    def promote_selected(self) -> None:
        item = self.list.currentItem()
        if not (self.api and item):
            return
        data = item.data(Qt.UserRole)
        api = self.api
        self.promote_btn.setEnabled(False)

        def ok(_):
            self.status.setText("✔ Image added to backgrounds.")
            self.load_uploads()
            self.load_backgrounds_gallery()

        self.tasks.run(lambda: api.promote(data["id"]), ok, self._error)
