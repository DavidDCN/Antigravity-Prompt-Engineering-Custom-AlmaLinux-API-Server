"""Widget that paints a server-provided image inside a dedicated open frame."""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QWidget


class BackgroundFrame(QWidget):
    def __init__(self, parent: QWidget | None = None, fit_mode: bool = True):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self.fit_mode = fit_mode

    def set_image(self, data: bytes) -> bool:
        pm = QPixmap()
        if not pm.loadFromData(data):
            return False
        self._pixmap = pm
        self.update()
        return True

    def toggle_fit_mode(self) -> bool:
        self.fit_mode = not self.fit_mode
        self.update()
        return self.fit_mode

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()

        g = QLinearGradient(0, 0, rect.width(), rect.height())
        g.setColorAt(0, QColor("#0b0f19"))
        g.setColorAt(1, QColor("#1e293b"))
        p.fillRect(rect, g)

        if self._pixmap and not self._pixmap.isNull():
            if self.fit_mode:
                scaled = self._pixmap.scaled(
                    rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                x = (rect.width() - scaled.width()) // 2
                y = (rect.height() - scaled.height()) // 2
                p.drawPixmap(x, y, scaled)
            else:
                scaled = self._pixmap.scaled(
                    rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                x = (scaled.width() - rect.width()) // 2
                y = (scaled.height() - rect.height()) // 2
                p.drawPixmap(rect, scaled, QRect(x, y, rect.width(), rect.height()))
        p.end()
