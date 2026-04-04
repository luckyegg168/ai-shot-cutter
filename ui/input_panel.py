"""InputPanel — URL, interval, API key, prompt type, start/stop controls.

Improvements v2:
  1. API key show/hide eye toggle
  2. Keyboard shortcuts (Ctrl+Enter = Start, Esc = Stop) — wired via MainWindow
  3. Drag & drop URL support
  4. Live frame counter in status bar — relayed via progress signal in MainWindow
  5. Collapsible form panel
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import JobConfig
from utils.i18n import SUPPORTED_LANGUAGES
from utils.settings import AppSettings


class InputPanel(QWidget):
    """Top panel containing all job configuration inputs."""

    job_requested = Signal(object)  # JobConfig

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._running = False
        self._form_collapsed = False
        self._setup_ui()
        self._load_settings()
        self._connect_signals()
        self._validate()
        # Feature 3: accept URL drag & drop
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    # Public properties (used by MainWindow for shortcuts)
    # ------------------------------------------------------------------
    @property
    def stop_button(self) -> QPushButton:
        return self._btn_stop

    @property
    def start_button(self) -> QPushButton:
        return self._btn_start

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 6)
        root.setSpacing(4)

        # ── Feature 5: Collapse / expand toggle bar ──────────────────
        self._collapse_btn = QPushButton("▼  " + self.tr("Job Configuration"))
        self._collapse_btn.setObjectName("collapse_toggle")
        self._collapse_btn.setFlat(True)
        root.addWidget(self._collapse_btn)

        # ── Form container (hidden when collapsed) ───────────────────
        self._form_widget = QGroupBox()
        form = QFormLayout(self._form_widget)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setContentsMargins(14, 12, 14, 12)

        # URL
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://www.youtube.com/watch?v=…")
        self._url_edit.setToolTip(self.tr("YouTube video URL · or drag-drop a URL here"))
        form.addRow(self.tr("YouTube URL"), self._url_edit)

        # Interval
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 300)
        self._interval_spin.setSuffix(" s")
        self._interval_spin.setToolTip(self.tr("Time between captured frames (seconds)"))
        form.addRow(self.tr("Interval (sec)"), self._interval_spin)

        # Feature 1: API key + eye toggle ────────────────────────────
        api_row = QHBoxLayout()
        api_row.setSpacing(0)
        self._api_edit = QLineEdit()
        self._api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_edit.setPlaceholderText("sk-…")
        self._api_edit.setToolTip(self.tr("OpenAI API Key (stored locally)"))
        self._api_edit.setStyleSheet("border-radius: 6px 0 0 6px;")
        self._eye_btn = QPushButton("👁")
        self._eye_btn.setObjectName("eye_btn")
        self._eye_btn.setCheckable(True)
        self._eye_btn.setToolTip(self.tr("Show / hide API key"))
        self._eye_btn.setFixedWidth(36)
        api_row.addWidget(self._api_edit)
        api_row.addWidget(self._eye_btn)
        form.addRow(self.tr("OpenAI API Key"), api_row)

        # Prompt type
        self._prompt_combo = QComboBox()
        self._prompt_combo.addItem(self.tr("Image Prompt"), "image")
        self._prompt_combo.addItem(self.tr("Video Prompt"), "video")
        form.addRow(self.tr("Prompt Type"), self._prompt_combo)

        # Max frames
        self._max_frames_spin = QSpinBox()
        self._max_frames_spin.setRange(0, 500)
        self._max_frames_spin.setSpecialValueText(self.tr("Unlimited"))
        self._max_frames_spin.setToolTip(self.tr("0 = unlimited"))
        form.addRow(self.tr("Max Frames (0=unlimited)"), self._max_frames_spin)

        # Output dir
        self._output_edit = QLineEdit()
        self._output_edit.setReadOnly(True)
        self._browse_btn = QPushButton(self.tr("Browse…"))
        self._browse_btn.setFixedWidth(80)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self._output_edit)
        dir_row.addWidget(self._browse_btn)
        form.addRow(self.tr("Output Dir"), dir_row)

        # Language selector
        self._lang_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(label, code)
        self._lang_combo.setToolTip(self.tr("Restart the app to apply language change"))
        form.addRow(self.tr("Language"), self._lang_combo)

        root.addWidget(self._form_widget)

        # ── Buttons row ──────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_start = QPushButton(self.tr("Start"))
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setToolTip("Ctrl+Enter")

        self._btn_stop = QPushButton(self.tr("Stop"))
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.setToolTip("Esc")

        self._btn_open = QPushButton(self.tr("Open Output"))

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_open)
        root.addLayout(btn_row)

        # Validation message
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #f38ba8; font-size: 11px; background: transparent;")
        self._error_label.setContentsMargins(4, 0, 0, 0)
        root.addWidget(self._error_label)

    def _load_settings(self) -> None:
        s = self._settings
        self._api_edit.setText(s.get_api_key())
        self._interval_spin.setValue(s.get_interval())
        self._output_edit.setText(str(s.get_output_dir()))
        self._max_frames_spin.setValue(s.get_max_frames())
        idx = self._prompt_combo.findData(s.get_prompt_type())
        if idx >= 0:
            self._prompt_combo.setCurrentIndex(idx)
        lang_idx = self._lang_combo.findData(s.get_language())
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)

    def _connect_signals(self) -> None:
        self._url_edit.textChanged.connect(self._validate)
        self._api_edit.textChanged.connect(self._validate)
        self._api_edit.textChanged.connect(lambda t: self._settings.set_api_key(t))
        self._interval_spin.valueChanged.connect(lambda v: self._settings.set_interval(v))
        self._max_frames_spin.valueChanged.connect(lambda v: self._settings.set_max_frames(v))
        self._prompt_combo.currentIndexChanged.connect(
            lambda _: self._settings.set_prompt_type(self._prompt_combo.currentData())
        )
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._request_stop)
        self._browse_btn.clicked.connect(self._browse_output)
        self._btn_open.clicked.connect(self._open_output)
        # Feature 1: eye toggle
        self._eye_btn.toggled.connect(self._toggle_api_visibility)
        # Feature 5: collapse toggle
        self._collapse_btn.clicked.connect(self._toggle_collapse)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate(self) -> None:
        url = self._url_edit.text().strip()
        key = self._api_edit.text().strip()

        errors: list[str] = []
        if not url:
            errors.append(self.tr("URL is required"))
        elif not url.startswith("http"):
            errors.append(self.tr("Invalid URL"))
        if not key:
            errors.append(self.tr("API key is required"))
        elif not key.startswith("sk-"):
            errors.append(self.tr("API key must start with sk-"))

        if errors:
            self._error_label.setText(" · ".join(errors))
            self._btn_start.setEnabled(False)
        else:
            self._error_label.clear()
            self._btn_start.setEnabled(not self._running)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_running(self, running: bool) -> None:
        self._running = running
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    # ------------------------------------------------------------------
    # Feature 1: API Key show/hide
    # ------------------------------------------------------------------
    def _toggle_api_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._api_edit.setEchoMode(mode)
        self._eye_btn.setText("🙈" if checked else "👁")

    # ------------------------------------------------------------------
    # Feature 5: Collapse / expand
    # ------------------------------------------------------------------
    def _toggle_collapse(self) -> None:
        self._form_collapsed = not self._form_collapsed
        self._form_widget.setVisible(not self._form_collapsed)
        arrow = "▶" if self._form_collapsed else "▼"
        self._collapse_btn.setText(f"{arrow}  " + self.tr("Job Configuration"))

    # ------------------------------------------------------------------
    # Feature 3: Drag & drop URL
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime.hasText() or mime.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        mime = event.mimeData()
        text = ""
        if mime.hasUrls():
            text = mime.urls()[0].toString()
        elif mime.hasText():
            text = mime.text().strip()

        if text.startswith("http"):
            self._url_edit.setText(text)
            # auto-expand if collapsed
            if self._form_collapsed:
                self._toggle_collapse()
            event.acceptProposedAction()
        else:
            event.ignore()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_start(self) -> None:
        config = JobConfig(
            url=self._url_edit.text().strip(),
            interval_sec=self._interval_spin.value(),
            api_key=self._api_edit.text().strip(),
            output_dir=Path(self._output_edit.text()),
            prompt_type=self._prompt_combo.currentData(),
            max_frames=self._max_frames_spin.value(),
        )
        self._settings.sync()
        self.job_requested.emit(config)

    def _on_language_changed(self) -> None:
        code: str = self._lang_combo.currentData()
        self._settings.set_language(code)
        QMessageBox.information(
            self,
            self.tr("Language"),
            self.tr("Restart the app to apply the language change."),
        )

    def _request_stop(self) -> None:
        self._btn_stop.setEnabled(False)

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select Output Folder"), self._output_edit.text()
        )
        if folder:
            self._output_edit.setText(folder)
            self._settings.set_output_dir(Path(folder))

    def _open_output(self) -> None:
        import subprocess
        import sys

        path = self._output_edit.text()
        if path:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
