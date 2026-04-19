"""MainWindow — assembles all panels."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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
from ui.settings_panel import SettingsPanel
from ui.toast import Toast
from ui.tools_panel import ToolsPanel
from utils.settings import AppSettings
from workers.pipeline_worker import PipelineWorker


class MainWindow(QMainWindow):
    """Main application window (1200×700 minimum)."""

    _regen_done = Signal(FrameResult)
    _regen_error = Signal(str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings
        self._worker: PipelineWorker | None = None
        self._last_output_dir: Path | None = None
        self._job_queue: list[JobConfig] = []
        self._job_start_time: float = 0.0

        self.setWindowTitle(self.tr("YouTube AI Frame Prompt Generator"))
        self.setMinimumSize(1200, 700)
        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()

        # Toast overlay
        self._toast = Toast(self)

        # Thread-safe regenerate signals
        self._regen_done.connect(self._prompt_panel.update_prompt)
        self._regen_error.connect(self._log_panel.log_error)

        # Restore always-on-top
        if self._settings.get_always_on_top():
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self._always_top_action.setChecked(True)

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
        self._tabs.addTab(self._input_panel, "⚙  " + self.tr("Job Settings"))

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

        # ── Tools tab (must be after _log_panel and _gallery) ────────
        self._tools_panel = ToolsPanel()
        self._tools_panel.set_all_frames_getter(lambda: self._gallery.get_all_frames())
        self._tools_panel.set_logger(self._log_panel.log_info)
        self._tabs.addTab(self._tools_panel, "🔧  " + self.tr("Tools"))

        # ── Settings tab ─────────────────────────────────────────────
        self._settings_panel = SettingsPanel(self._settings)
        self._tabs.addTab(self._settings_panel, "⚙  " + self.tr("Settings"))

        # Wire settings panel to input panel for validation & job creation
        self._input_panel.set_settings_panel(self._settings_panel)
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
        self._gallery.card_double_clicked.connect(self._on_frame_zoom)
        self._prompt_panel.regenerate_requested.connect(self._on_regenerate)

        # Wire settings: live theme toggle
        self._settings_panel.theme_changed.connect(self._apply_theme_live)

        # Wire batch actions: give prompt_panel access to gallery frames
        self._prompt_panel.set_all_frames_getter(self._gallery.get_all_frames)

    # Feature: keyboard shortcuts (including frame navigation)
    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Return"), self, self._input_panel.start_button.click)
        QShortcut(QKeySequence("Escape"), self, self._input_panel.stop_button.click)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._prompt_panel._copy_btn.click)
        QShortcut(QKeySequence("Left"), self, self._gallery.select_prev)
        QShortcut(QKeySequence("Right"), self, self._gallery.select_next)
        QShortcut(QKeySequence("Home"), self, self._gallery.select_first)
        QShortcut(QKeySequence("End"), self, self._gallery.select_last)
        QShortcut(QKeySequence("Ctrl+/"), self, self._show_shortcuts_help)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu(self.tr("File"))
        file_menu.addAction(self.tr("Save Project"), self._tools_panel._on_save_project)
        file_menu.addAction(self.tr("Load Project"), self._tools_panel._on_load_project)
        file_menu.addSeparator()
        file_menu.addAction(self.tr("Export HTML Report"), self._export_html)
        file_menu.addAction(self.tr("Export CSV"), self._export_csv)
        file_menu.addSeparator()
        file_menu.addAction(self.tr("Open Output Folder"), self._open_output)
        file_menu.addSeparator()
        file_menu.addAction(self.tr("Exit"), self.close)

        view_menu = menubar.addMenu(self.tr("View"))
        view_menu.addAction(self.tr("Prompt History"), self._show_prompt_history)
        view_menu.addSeparator()
        self._always_top_action = view_menu.addAction(self.tr("Always on Top"))
        self._always_top_action.setCheckable(True)
        self._always_top_action.toggled.connect(self._toggle_always_on_top)

        help_menu = menubar.addMenu(self.tr("Help"))
        help_menu.addAction(self.tr("Keyboard Shortcuts") + "\tCtrl+/", self._show_shortcuts_help)
        help_menu.addSeparator()
        help_menu.addAction(self.tr("About"), self._show_about)

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------
    def _on_job_requested(self, config: JobConfig) -> None:
        if self._worker and self._worker.isRunning():
            # Queue batch jobs
            self._job_queue.append(config)
            self._log_panel.log_info(
                self.tr("Queued: %1 (%2 in queue)").replace("%1", config.url).replace("%2", str(len(self._job_queue)))
            )
            return

        self._start_job(config)

    def _start_job(self, config: JobConfig) -> None:
        self._gallery.clear()
        self._log_panel.reset_progress()
        self._log_panel.log_info(self.tr("Starting job: %1").replace("%1", config.url))
        self._last_output_dir = config.output_dir
        self._job_start_time = time.time()

        self._worker = PipelineWorker(config)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.job_finished.connect(self._on_job_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.metadata_ready.connect(self._on_metadata)

        # Let tools panel know the video path
        self._worker.metadata_ready.connect(self._on_set_tools_video)

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
            self.tr("Frame %1 | %2 | %3…").replace("%1", str(frame.index)).replace("%2", frame.timestamp_label).replace("%3", frame.prompt[:60])
        )
        # Feature: persist prompt history
        if self._worker:
            from utils.prompt_history import append_entry
            append_entry(
                url=self._worker._config.url,
                frame_index=frame.index,
                timestamp_label=frame.timestamp_label,
                prompt=frame.prompt,
                prompt_type=self._worker._config.prompt_type,
            )

    def _on_set_tools_video(self, meta: dict) -> None:
        video_path = meta.get("video_path")
        if video_path:
            self._tools_panel.set_video_path(Path(video_path))

    def _on_metadata(self, meta: dict) -> None:
        """Log video metadata when available."""
        parts = []
        if "width" in meta and "height" in meta:
            parts.append(f"{meta['width']}×{meta['height']}")
        if meta.get("fps"):
            parts.append(f"{meta['fps']} fps")
        if meta.get("codec"):
            parts.append(meta["codec"])
        if meta.get("duration"):
            dur = float(meta["duration"])
            mins = int(dur) // 60
            secs = int(dur) % 60
            parts.append(f"{mins}m{secs}s")
            # Feature: Duration-based estimation
            if self._worker:
                interval = self._worker._config.interval_sec
                est_frames = max(1, int(dur / interval))
                self._log_panel.log_info(
                    self.tr("Estimated frames: ~%1 (every %2s)")
                    .replace("%1", str(est_frames))
                    .replace("%2", str(interval))
                )
        if meta.get("format_name"):
            parts.append(meta["format_name"])
        if parts:
            self._log_panel.log_info(f"📹 Video: {' · '.join(parts)}")

    def _on_job_finished(self, result: JobResult) -> None:
        if result.success:
            elapsed = time.time() - self._job_start_time
            msg = self.tr("Job completed — %1 frames").replace("%1", str(len(result.frames)))
            self._log_panel.log_info(msg)
            self.statusBar().showMessage(msg)
            self._toast.show_message(msg, "info")
            self._show_session_summary(result, elapsed)
            # Feature: auto-open output folder
            if self._settings.get_auto_open_output():
                self._open_output()
        else:
            msg = self.tr("Job finished with errors: %1").replace("%1", result.error_message or "")
            self._log_panel.log_warning(msg)
            self.statusBar().showMessage(msg)
            self._toast.show_message(msg, "warning")

        # Process next job in batch queue
        if self._job_queue:
            next_config = self._job_queue.pop(0)
            self._log_panel.log_info(
                self.tr("Starting next queued job… (%1 remaining)").replace("%1", str(len(self._job_queue)))
            )
            self._start_job(next_config)
        else:
            self._input_panel.set_running(False)

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
        use_local = self._settings.get_use_local_model()
        local_url = self._settings.get_local_model_url()
        model_name = self._settings.get_model_name()
        custom_prompt = self._settings.get_custom_system_prompt()
        regen_done = self._regen_done
        regen_error = self._regen_error

        class _Task(QRunnable):
            def __init__(self_, f: FrameResult) -> None:
                super().__init__()
                self_._frame = f

            @Slot()
            def run(self_) -> None:
                try:
                    new_prompt = analyze_frame(
                        self_._frame.image_path,
                        api_key,
                        prompt_type,
                        use_local_model=use_local,
                        local_model_url=local_url,
                        model_name=model_name,
                        custom_system_prompt=custom_prompt,
                    )
                    new_result = FrameResult(
                        index=self_._frame.index,
                        timestamp_sec=self_._frame.timestamp_sec,
                        image_path=self_._frame.image_path,
                        prompt=new_prompt,
                    )
                    regen_done.emit(new_result)
                except VisionError as exc:
                    regen_error.emit(str(exc))

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

    # ------------------------------------------------------------------
    # Feature: Frame zoom viewer (double-click)
    # ------------------------------------------------------------------
    def _on_frame_zoom(self, frame: FrameResult) -> None:
        from ui.zoom_viewer import ZoomViewer
        dlg = ZoomViewer(frame, self)
        dlg.exec()

    # ------------------------------------------------------------------
    # Feature: Export HTML report
    # ------------------------------------------------------------------
    def _export_html(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        from utils.file_utils import write_html_report

        frames = self._gallery.get_all_frames()
        if not frames:
            QMessageBox.information(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export HTML Report"), "report.html", "HTML (*.html)"
        )
        if path:
            write_html_report(Path(path), frames)
            self._log_panel.log_info(self.tr("HTML report exported: %1").replace("%1", path))

    # ------------------------------------------------------------------
    # Feature: Export CSV
    # ------------------------------------------------------------------
    def _export_csv(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        from utils.file_utils import write_csv

        frames = self._gallery.get_all_frames()
        if not frames:
            QMessageBox.information(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export CSV"), "frames.csv", "CSV (*.csv)"
        )
        if path:
            write_csv(Path(path), frames)
            self._log_panel.log_info(self.tr("CSV exported: %1").replace("%1", path))

    # ------------------------------------------------------------------
    # Feature: Prompt history viewer
    # ------------------------------------------------------------------
    def _show_prompt_history(self) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout
        from utils.prompt_history import load_history

        entries = load_history()
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Prompt History"))
        dlg.resize(700, 500)
        lay = QVBoxLayout(dlg)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        if entries:
            lines = []
            for e in reversed(entries):
                lines.append(
                    f"[{e.get('created_at', '')}]  Frame {e.get('frame_index', '?')}  "
                    f"({e.get('timestamp', '')})\n{e.get('prompt', '')}\n"
                )
            text.setPlainText("\n".join(lines))
        else:
            text.setPlainText(self.tr("No history yet."))
        lay.addWidget(text)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        dlg.exec()

    # ------------------------------------------------------------------
    # Feature: Live theme toggle
    # ------------------------------------------------------------------
    def _apply_theme_live(self, theme: str) -> None:
        qss_name = "styles_light.qss" if theme == "light" else "styles.qss"
        qss_path = Path(__file__).parent / qss_name
        if qss_path.exists():
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Feature F-18: Clipboard URL Auto-detect
    # ------------------------------------------------------------------
    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        if event.type() == QEvent.Type.WindowActivate:
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            if (
                text.startswith("http")
                and "youtube.com" in text
                and text != self._input_panel._url_edit.toPlainText().strip()
            ):
                self._input_panel.show_clipboard_banner(text)
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Feature F-25: Always on Top
    # ------------------------------------------------------------------
    def _toggle_always_on_top(self, checked: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()
        self._settings.set_always_on_top(checked)

    # ------------------------------------------------------------------
    # Feature F-20: Keyboard Shortcuts Help
    # ------------------------------------------------------------------
    def _show_shortcuts_help(self) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        shortcuts = [
            ("Ctrl+Enter", self.tr("Start job")),
            ("Escape", self.tr("Stop job")),
            ("←  /  →", self.tr("Navigate frames")),
            ("Home  /  End", self.tr("First / Last frame")),
            ("Ctrl+Shift+C", self.tr("Copy current prompt")),
            ("Ctrl+/", self.tr("Show this help")),
        ]
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Keyboard Shortcuts"))
        dlg.setMinimumWidth(380)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(6)
        for key, desc in shortcuts:
            row_lbl = QLabel(f"<b>{key}</b>  —  {desc}")
            row_lbl.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(row_lbl)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    # ------------------------------------------------------------------
    # Feature F-24: Session Summary Dialog
    # ------------------------------------------------------------------
    def _show_session_summary(self, result: JobResult, elapsed: float) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        frames = result.frames
        if not frames:
            return

        prompt_lengths = [len(f.prompt) for f in frames]
        avg_len = sum(prompt_lengths) // len(prompt_lengths) if prompt_lengths else 0
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60

        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Session Summary"))
        dlg.setMinimumWidth(360)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)

        def _stat(label: str, value: str) -> QLabel:
            lbl = QLabel(f"<b>{label}</b>  {value}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            return lbl

        layout.addWidget(_stat(self.tr("Frames analyzed:"), str(len(frames))))
        layout.addWidget(_stat(self.tr("Elapsed time:"), f"{mins}m {secs}s"))
        layout.addWidget(_stat(self.tr("Avg prompt length:"), f"{avg_len} chars"))
        layout.addWidget(_stat(self.tr("Longest prompt:"), f"{max(prompt_lengths)} chars"))

        btns = QDialogButtonBox()
        open_btn = btns.addButton(self.tr("Open Output Folder"), QDialogButtonBox.ButtonRole.ActionRole)
        open_btn.clicked.connect(self._open_output)
        btns.addButton(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        self._settings.sync()
        super().closeEvent(event)
