"""MainWindow — assembles all panels."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QWidget,
)

from core.models import FrameResult, JobConfig, JobResult
from ui.gallery_widget import GalleryWidget
from ui.input_panel import InputPanel
from ui.log_panel import LogPanel
from ui.prompt_panel import PromptPanel
from utils.settings import AppSettings
from workers.pipeline_worker import PipelineWorker


class MainWindow(QMainWindow):
    """Main application window (1200×700 minimum)."""

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings
        self._worker: PipelineWorker | None = None
        self._last_output_dir: Path | None = None

        self.setWindowTitle(self.tr("YouTube AI Frame Prompt Generator"))
        self.setMinimumSize(1200, 700)
        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        from PySide6.QtWidgets import QTabWidget, QVBoxLayout

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Main horizontal splitter: left tabs | right results ───────
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: QTabWidget ─────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setMinimumWidth(380)
        self._tabs.setMaximumWidth(560)
        self._tabs.setDocumentMode(True)

        self._input_panel = InputPanel(self._settings)
        self._tabs.addTab(self._input_panel, self.tr("Job Settings"))

        main_splitter.addWidget(self._tabs)

        # ── Right: vertical splitter (gallery+prompt | log) ──────────
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Gallery | Prompt (horizontal)
        mid_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._gallery = GalleryWidget()
        self._prompt_panel = PromptPanel()
        mid_splitter.addWidget(self._gallery)
        mid_splitter.addWidget(self._prompt_panel)
        mid_splitter.setStretchFactor(0, 2)
        mid_splitter.setStretchFactor(1, 1)
        right_splitter.addWidget(mid_splitter)

        # Log
        self._log_panel = LogPanel()
        right_splitter.addWidget(self._log_panel)
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 0)
        right_splitter.setSizes([600, 180])

        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([440, 760])

        root_layout.addWidget(main_splitter)

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(self.tr("Ready"))

        # Connect signals
        self._input_panel.job_requested.connect(self._on_job_requested)
        self._input_panel.stop_button.clicked.connect(self._on_stop_requested)
        self._gallery.card_selected.connect(self._prompt_panel.show_frame)
        self._prompt_panel.regenerate_requested.connect(self._on_regenerate)

        # Wire batch actions: give prompt_panel access to gallery frames
        self._prompt_panel.set_all_frames_getter(self._gallery.get_all_frames)

    # Feature: keyboard shortcuts (including frame navigation)
    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Return"), self, self._input_panel.start_button.click)
        QShortcut(QKeySequence("Escape"), self, self._input_panel.stop_button.click)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._prompt_panel._copy_btn.click)
        QShortcut(QKeySequence("Left"), self, self._gallery.select_prev)
        QShortcut(QKeySequence("Right"), self, self._gallery.select_next)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu(self.tr("File"))
        file_menu.addAction(self.tr("Open Output Folder"), self._open_output)
        file_menu.addSeparator()
        file_menu.addAction(self.tr("Exit"), self.close)

        help_menu = menubar.addMenu(self.tr("Help"))
        help_menu.addAction(self.tr("About"), self._show_about)

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------
    def _on_job_requested(self, config: JobConfig) -> None:
        if self._worker and self._worker.isRunning():
            return

        self._gallery.clear()
        self._log_panel.reset_progress()
        self._log_panel.log_info(self.tr(f"Starting job: {config.url}"))
        self._last_output_dir = config.output_dir

        self._worker = PipelineWorker(config)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.job_finished.connect(self._on_job_finished)
        self._worker.error_occurred.connect(self._on_error)

        self._input_panel.set_running(True)
        self.statusBar().showMessage(self.tr("Running…"))
        self._worker.start()

    def _on_stop_requested(self) -> None:
        if self._worker and self._worker.isRunning():
            self._log_panel.log_warning(self.tr("Cancelling job…"))
            self._worker.stop()

    # ------------------------------------------------------------------
    # Worker signal handlers
    # ------------------------------------------------------------------
    def _on_progress(self, current: int, total: int, message: str) -> None:
        self._log_panel.set_progress(current, total, message)
        # Feature 4: live frame counter in status bar
        if total > 0:
            self.statusBar().showMessage(f"Frame {current}/{total}  ·  {message}")
        else:
            self.statusBar().showMessage(message)

    def _on_frame_ready(self, frame: FrameResult) -> None:
        self._gallery.add_frame_card(frame)
        self._log_panel.log_info(
            self.tr(f"Frame {frame.index} | {frame.timestamp_label} | {frame.prompt[:60]}…")
        )

    def _on_job_finished(self, result: JobResult) -> None:
        self._input_panel.set_running(False)
        if result.success:
            msg = self.tr(f"Job completed — {len(result.frames)} frames")
            self._log_panel.log_info(msg)
            self.statusBar().showMessage(msg)
        else:
            msg = self.tr(f"Job finished with errors: {result.error_message}")
            self._log_panel.log_warning(msg)
            self.statusBar().showMessage(msg)

    def _on_error(self, message: str) -> None:
        self._input_panel.set_running(False)
        self._log_panel.log_error(message)
        self.statusBar().showMessage(self.tr("Error occurred"))
        QMessageBox.critical(self, self.tr("Error"), message)

    # ------------------------------------------------------------------
    # Regenerate
    # ------------------------------------------------------------------
    def _on_regenerate(self, frame: FrameResult) -> None:
        """Re-analyze a single frame (runs in a thread)."""
        from PySide6.QtCore import QRunnable, QThreadPool, Slot
        from core.vision import analyze_frame, VisionError

        api_key = self._settings.get_api_key()
        prompt_type = self._settings.get_prompt_type()

        class _Task(QRunnable):
            def __init__(self_, f: FrameResult) -> None:
                super().__init__()
                self_._frame = f

            @Slot()
            def run(self_) -> None:
                try:
                    new_prompt = analyze_frame(self_._frame.image_path, api_key, prompt_type)
                    new_result = FrameResult(
                        index=self_._frame.index,
                        timestamp_sec=self_._frame.timestamp_sec,
                        image_path=self_._frame.image_path,
                        prompt=new_prompt,
                    )
                    self._prompt_panel.update_prompt(new_result)
                except VisionError as exc:
                    self._log_panel.log_error(str(exc))

        QThreadPool.globalInstance().start(_Task(frame))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _open_output(self) -> None:
        path = str(self._last_output_dir or self._settings.get_output_dir())
        if sys.platform == "win32":
            subprocess.Popen(["explorer", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("關於"),
            "<b>YouTube AI 影格 Prompt 生成器</b> v1.0.0<br>"
            "PySide6 · yt-dlp · ffmpeg · GPT-4o<br><br>"
            "© 2026 luckyegg168",
        )

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        self._settings.sync()
        super().closeEvent(event)
