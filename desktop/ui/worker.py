"""Run blocking network calls off the UI thread."""
from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], Any]):
        super().__init__()
        self.fn = fn
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as e:  # noqa: BLE001 - report every failure to the UI
            msg = str(e) or e.__class__.__name__
            if not msg:
                msg = traceback.format_exc()
            self.signals.failed.emit(msg)
        else:
            self.signals.done.emit(result)


class TaskRunner:
    """Keeps references to running tasks so their signal objects aren't garbage-collected."""

    def __init__(self) -> None:
        self._pool = QThreadPool.globalInstance()
        self._active: set[_Task] = set()

    def run(self, fn: Callable[[], Any], on_done: Callable[[Any], None] | None = None,
            on_error: Callable[[str], None] | None = None) -> None:
        task = _Task(fn)
        task.setAutoDelete(False)
        self._active.add(task)

        def finish() -> None:
            self._active.discard(task)

        if on_done:
            task.signals.done.connect(on_done)
        if on_error:
            task.signals.failed.connect(on_error)
        task.signals.done.connect(lambda _: finish())
        task.signals.failed.connect(lambda _: finish())
        self._pool.start(task)
