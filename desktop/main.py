"""ATTRial desktop client: entry point.

Run:    python desktop/main.py
Build:  pyinstaller --noconfirm --windowed --name ATTRialClient desktop/main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python desktop/main.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ATTRial Client")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
