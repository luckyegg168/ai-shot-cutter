"""InputPanel — URL, interval, API key, prompt type, start/stop controls."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import JobConfig
from utils.settings import AppSettings


class InputPanel(QWidget):
    """Top panel containing all job configuration inputs."""

    job_requested = Signal(object)   # JobConfig

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._running = False
        self._setup_ui()
        self._load_settings()
        self._connect_signals()
        self._validate()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        group = QGroupBox(self.tr("Job Configuration"))
        form = QFormLayout(group)
        form.setHorizontalSpacing(12)

        # URL
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://www.youtube.com/watch?v=…")
        self._url_edit.setToolTip(self.tr("YouTube video URL"))
        form.addRow(self.tr("YouTube URL"), self._url_edit)

        # Interval
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 300)
        self._interval_spin.setSuffix(" s")
        self._interval_spin.setToolTip(self.tr("Time between captured frames (seconds)"))
        form.addRow(self.tr("Interval (sec)"), self._interval_spin)

        # API key
        self._api_edit = QLineEdit()
        self._api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_edit.setPlaceholderText("sk-…")
        self._api_edit.setToolTip(self.tr("OpenAI API Key (stored locally in QSettings)"))
        form.addRow(self.tr("OpenAI API Key"), self._api_edit)

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

        root.addWidget(group)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_start = QPushButton(self.tr("Start"))
        self._btn_start.setObjectName("btn_start")

        self._btn_stop = QPushButton(self.tr("Stop"))
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.setEnabled(False)

        self._btn_open = QPushButton(self.tr("Open Output"))

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_open)
        root.addLayout(btn_row)

        # Validation message
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #f38ba8; font-size: 11px;")
        root.addWidget(self._error_label)

    def _load_settings(self) -> None:
        s = self._settings
        self._api_edit.setText(s.get_api_key())
        self._interval_spin.setValue(s.get_interval())
        self._output_edit.setText(str(s.get_output_dir()))
        self._max_frames_spin.setValue(s.get_max_frames())
        # prompt type
        idx = self._prompt_combo.findData(s.get_prompt_type())
        if idx >= 0:
            self._prompt_combo.setCurrentIndex(idx)

    def _connect_signals(self) -> None:
        self._url_edit.textChanged.connect(self._validate)
        self._api_edit.textChanged.connect(self._validate)
        self._api_edit.textChanged.connect(lambda t: self._settings.set_api_key(t))
        self._interval_spin.valueChanged.connect(lambda v: self._settings.set_interval(v))
        self._max_frames_spin.valueChanged.connect(lambda v: self._settings.set_max_frames(v))
        self._prompt_combo.currentIndexChanged.connect(
            lambda _: self._settings.set_prompt_type(self._prompt_combo.currentData())
        )
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._request_stop)
        self._browse_btn.clicked.connect(self._browse_output)
        self._btn_open.clicked.connect(self._open_output)

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
        import subprocess, sys

        path = self._output_edit.text()
        if path:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

    # ------------------------------------------------------------------
    # External state setters (called by MainWindow)
    # ------------------------------------------------------------------
    def set_running(self, running: bool) -> None:
        self._running = running
        self._btn_stop.setEnabled(running)
        if running:
            self._btn_start.setEnabled(False)
        else:
            self._validate()

    @property
    def stop_button(self) -> QPushButton:
        return self._btn_stop
