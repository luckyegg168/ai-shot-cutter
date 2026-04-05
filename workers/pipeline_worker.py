"""QThread worker that wraps Pipeline.run."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from core.models import FrameResult, JobConfig, JobResult
from core.pipeline import Pipeline


class PipelineWorker(QThread):
    """Background thread that runs the full download→extract→vision pipeline."""

    progress_updated = Signal(int, int, str)   # current, total, message
    frame_ready = Signal(object)               # FrameResult
    job_finished = Signal(object)              # JobResult
    error_occurred = Signal(str)               # error message
    metadata_ready = Signal(object)            # dict with video metadata

    def __init__(self, config: JobConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Request cancellation; blocks until the thread finishes."""
        self._stop_event.set()
        self.wait()

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        pipeline = Pipeline()
        try:
            result = pipeline.run(
                self._config,
                on_progress=self._on_progress,
                on_frame_done=self._on_frame_done,
                stop_event=self._stop_event,
                on_metadata=self._on_metadata,
            )
            self.job_finished.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ------------------------------------------------------------------
    # Internal callbacks (called from worker thread — signals marshal to GUI)
    # ------------------------------------------------------------------
    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.progress_updated.emit(current, total, message)

    def _on_frame_done(self, frame: FrameResult) -> None:
        self.frame_ready.emit(frame)

    def _on_metadata(self, meta: dict) -> None:
        self.metadata_ready.emit(meta)
