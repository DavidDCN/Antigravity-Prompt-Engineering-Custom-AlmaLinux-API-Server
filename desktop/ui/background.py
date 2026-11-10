"""Widget that paints a server-provided image as a full-window background."""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QWidget


class BackgroundFrame(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None

    def set_image(self, data: bytes) -> bool:
        pm = QPixmap()
        if not pm.loadFromData(data):
            return False
        self._pixmap = pm
        self.update()
        return True

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        if self._pixmap and not self._pixmap.isNull():
            # "cover" scaling: fill the window, crop the overflow, keep it centered
            scaled = self._pixmap.scaled(rect.size(), Qt.KeepAspectRatioByExpanding,
                                         Qt.SmoothTransformation)
            x = (scaled.width() - rect.width()) // 2
            y = (scaled.height() - rect.height()) // 2
            p.drawPixmap(rect, scaled, QRect(x, y, rect.width(), rect.height()))
            p.fillRect(rect, QColor(0, 0, 0, 70))  # slight dim so panels stay readable
        else:
            g = QLinearGradient(0, 0, rect.width(), rect.height())
            g.setColorAt(0, QColor("#1e2a3a"))
            g.setColorAt(1, QColor("#3a1e3a"))
            p.fillRect(rect, g)
        p.end()
