"""InputPanel — URL, interval, API key, prompt type, start/stop controls."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import JobConfig
from utils.i18n import SUPPORTED_LANGUAGES
from utils.settings import AppSettings

_FIELD_H = 34   # uniform height for all input widgets
_LBL_W  = 170  # fixed label column width


class InputPanel(QWidget):
    """Configuration form — lives inside the 任務設定 tab."""

    job_requested = Signal(object)  # JobConfig

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._running = False
        self._setup_ui()
        self._load_settings()
        self._connect_signals()
        self._validate()
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    # Public properties
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
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(0)

        # ── Grid form ─────────────────────────────────────────────────
        # 4-column: [label | field | label | field]
        # Full-width rows span columns 1-3.
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnMinimumWidth(0, _LBL_W)
        grid.setColumnMinimumWidth(2, _LBL_W)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        lbl = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # Row 0 ── YouTube URL (multi-line for batch) ────────────────
        grid.addWidget(self._lbl("YouTube URL"), 0, 0, lbl)
        self._url_edit = QPlainTextEdit()
        self._url_edit.setFixedHeight(60)
        self._url_edit.setPlaceholderText(
            "https://www.youtube.com/watch?v=…\n"
            "(one URL per line for batch processing)"
        )
        self._url_edit.setToolTip(self.tr("YouTube video URL"))
        grid.addWidget(self._url_edit, 0, 1, 1, 3)

        # Row 1 ── Interval  |  Prompt Type ──────────────────────────
        grid.addWidget(self._lbl(self.tr("Interval (sec)")), 1, 0, lbl)
        self._interval_spin = QSpinBox()
        self._interval_spin.setFixedHeight(_FIELD_H)
        self._interval_spin.setRange(1, 300)
        self._interval_spin.setSuffix(" s")
        self._interval_spin.setToolTip(self.tr("Time between captured frames (seconds)"))
        grid.addWidget(self._interval_spin, 1, 1)

        grid.addWidget(self._lbl(self.tr("Prompt Type")), 1, 2, lbl)
        self._prompt_combo = QComboBox()
        self._prompt_combo.setFixedHeight(_FIELD_H)
        self._prompt_combo.addItem(self.tr("Image Prompt"), "image")
        self._prompt_combo.addItem(self.tr("Video Prompt"), "video")
        self._prompt_combo.setMinimumWidth(140)
        grid.addWidget(self._prompt_combo, 1, 3)

        # Row 2 ── Max Frames  |  Language ────────────────────────────
        grid.addWidget(self._lbl(self.tr("Max Frames (0=unlimited)")), 2, 0, lbl)
        self._max_frames_spin = QSpinBox()
        self._max_frames_spin.setFixedHeight(_FIELD_H)
        self._max_frames_spin.setRange(0, 500)
        self._max_frames_spin.setSpecialValueText(self.tr("Unlimited"))
        self._max_frames_spin.setToolTip(self.tr("0 = unlimited"))
        grid.addWidget(self._max_frames_spin, 2, 1)

        grid.addWidget(self._lbl(self.tr("Language")), 2, 2, lbl)
        self._lang_combo = QComboBox()
        self._lang_combo.setFixedHeight(_FIELD_H)
        for code, label in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(label, code)
        self._lang_combo.setToolTip(self.tr("Restart to apply language"))
        grid.addWidget(self._lang_combo, 2, 3)

        # Row 2.5 ── Video Resolution  |  Theme Toggle ───────────────
        grid.addWidget(self._lbl(self.tr("Video Resolution")), 3, 0, lbl)
        self._resolution_combo = QComboBox()
        self._resolution_combo.setFixedHeight(_FIELD_H)
        self._resolution_combo.addItem("720p", "720")
        self._resolution_combo.addItem("1080p", "1080")
        self._resolution_combo.addItem(self.tr("Best Quality"), "best")
        self._resolution_combo.setToolTip(self.tr("Video resolution limit for yt-dlp"))
        self._resolution_combo.setMinimumWidth(120)
        grid.addWidget(self._resolution_combo, 3, 1)

        grid.addWidget(self._lbl(self.tr("Theme")), 3, 2, lbl)
        self._theme_combo = QComboBox()
        self._theme_combo.setFixedHeight(_FIELD_H)
        self._theme_combo.addItem(self.tr("Dark Theme"), "dark")
        self._theme_combo.addItem(self.tr("Light Theme"), "light")
        self._theme_combo.setToolTip(self.tr("Toggle dark / light appearance"))
        self._theme_combo.setMinimumWidth(120)
        grid.addWidget(self._theme_combo, 3, 3)

        # Row 3 ── OpenAI API Key (full width) + eye ──────────────────
        grid.addWidget(self._lbl(self.tr("OpenAI API Key")), 4, 0, lbl)
        self._api_edit = QLineEdit()
        self._api_edit.setFixedHeight(_FIELD_H)
        self._api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_edit.setPlaceholderText("sk-…")
        self._api_edit.setToolTip(self.tr("OpenAI API Key (stored locally only)"))
        self._eye_btn = QPushButton("👁")
        self._eye_btn.setObjectName("eye_btn")
        self._eye_btn.setCheckable(True)
        self._eye_btn.setFixedSize(36, _FIELD_H)
        self._eye_btn.setToolTip(self.tr("Show / Hide"))
        api_row = QHBoxLayout()
        api_row.setSpacing(0)
        api_row.setContentsMargins(0, 0, 0, 0)
        api_row.addWidget(self._api_edit)
        api_row.addWidget(self._eye_btn)
        api_wrap = QWidget()
        api_wrap.setLayout(api_row)
        grid.addWidget(api_wrap, 4, 1, 1, 3)

        # Row 5 ── Output Dir (full width) + Browse ───────────────────
        grid.addWidget(self._lbl(self.tr("Output Dir")), 5, 0, lbl)
        self._output_edit = QLineEdit()
        self._output_edit.setFixedHeight(_FIELD_H)
        self._output_edit.setReadOnly(True)
        self._browse_btn = QPushButton(self.tr("Browse…"))
        self._browse_btn.setFixedSize(72, _FIELD_H)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        dir_row.setContentsMargins(0, 0, 0, 0)
        dir_row.addWidget(self._output_edit)
        dir_row.addWidget(self._browse_btn)
        dir_wrap = QWidget()
        dir_wrap.setLayout(dir_row)
        grid.addWidget(dir_wrap, 5, 1, 1, 3)

        # Row 6 ── Local Model toggle  |  Model Name ─────────────────
        grid.addWidget(self._lbl(self.tr("Local Model")), 6, 0, lbl)
        self._local_model_check = QCheckBox(self.tr("Use Local Model"))
        self._local_model_check.setFixedHeight(_FIELD_H)
        grid.addWidget(self._local_model_check, 6, 1)

        grid.addWidget(self._lbl(self.tr("Model Name")), 6, 2, lbl)
        self._model_name_edit = QLineEdit()
        self._model_name_edit.setFixedHeight(_FIELD_H)
        self._model_name_edit.setPlaceholderText("gpt-4o / llava / llama3.2-vision")
        self._model_name_edit.setToolTip(self.tr("Model name for API"))
        grid.addWidget(self._model_name_edit, 6, 3)

        # Row 7 ── Local Model URL (full width) ──────────────────────
        grid.addWidget(self._lbl(self.tr("Model API URL")), 7, 0, lbl)
        self._model_url_edit = QLineEdit()
        self._model_url_edit.setFixedHeight(_FIELD_H)
        self._model_url_edit.setPlaceholderText("http://192.168.1.100:11434/v1")
        self._model_url_edit.setToolTip(self.tr("OpenAI-compatible API endpoint"))
        grid.addWidget(self._model_url_edit, 7, 1, 1, 3)

        # Row 8 ── Blur Threshold  |  (empty) ────────────────────────
        grid.addWidget(self._lbl(self.tr("Blur Threshold")), 8, 0, lbl)
        self._blur_spin = QDoubleSpinBox()
        self._blur_spin.setFixedHeight(_FIELD_H)
        self._blur_spin.setRange(0.0, 9999.0)
        self._blur_spin.setSingleStep(10.0)
        self._blur_spin.setDecimals(1)
        self._blur_spin.setSpecialValueText(self.tr("Disabled"))
        self._blur_spin.setToolTip(self.tr("Skip frames with blur score below this (0=disabled)"))
        grid.addWidget(self._blur_spin, 8, 1)

        # Row 9 ── Custom System Prompt (full width) ──────────────────
        grid.addWidget(self._lbl(self.tr("System Prompt")), 9, 0, lbl)
        self._system_prompt_edit = QPlainTextEdit()
        self._system_prompt_edit.setFixedHeight(60)
        self._system_prompt_edit.setPlaceholderText(
            self.tr("Leave empty to use default prompt…")
        )
        self._system_prompt_edit.setToolTip(self.tr("Custom system prompt (overrides default)"))
        grid.addWidget(self._system_prompt_edit, 9, 1, 1, 3)

        root.addLayout(grid)
        root.addSpacing(20)

        # ── Divider ───────────────────────────────────────────────────
        from PySide6.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)
        root.addSpacing(12)

        # ── Buttons row ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_start = QPushButton(self.tr("Start"))
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setFixedHeight(38)
        self._btn_start.setToolTip("Ctrl+Enter")
        self._btn_start.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._btn_stop = QPushButton(self.tr("Stop"))
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.setFixedHeight(38)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setToolTip("Esc")
        self._btn_stop.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._btn_open = QPushButton(self.tr("Open Output"))
        self._btn_open.setFixedHeight(38)

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_open)
        root.addLayout(btn_row)
        root.addSpacing(8)

        # ── Validation message ────────────────────────────────────────
        self._error_label = QLabel()
        self._error_label.setStyleSheet(
            "color: #f38ba8; font-size: 11px; background: transparent;"
        )
        root.addWidget(self._error_label)
        root.addStretch()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 13px;")
        lbl.setMinimumWidth(_LBL_W)
        return lbl

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
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
        res_idx = self._resolution_combo.findData(s.get_resolution())
        if res_idx >= 0:
            self._resolution_combo.setCurrentIndex(res_idx)
        theme_idx = self._theme_combo.findData(s.get_theme())
        if theme_idx >= 0:
            self._theme_combo.setCurrentIndex(theme_idx)
        # New settings
        self._local_model_check.setChecked(s.get_use_local_model())
        self._model_url_edit.setText(s.get_local_model_url())
        self._model_name_edit.setText(s.get_model_name())
        self._system_prompt_edit.setPlainText(s.get_custom_system_prompt())
        self._blur_spin.setValue(s.get_blur_threshold())
        self._on_local_model_toggled(s.get_use_local_model())

    def _connect_signals(self) -> None:
        self._url_edit.textChanged.connect(self._validate)
        self._api_edit.textChanged.connect(self._validate)
        self._api_edit.textChanged.connect(lambda t: self._settings.set_api_key(t))
        self._interval_spin.valueChanged.connect(lambda v: self._settings.set_interval(v))
        self._max_frames_spin.valueChanged.connect(lambda v: self._settings.set_max_frames(v))
        self._prompt_combo.currentIndexChanged.connect(
            lambda _: self._settings.set_prompt_type(self._prompt_combo.currentData())
        )
        self._resolution_combo.currentIndexChanged.connect(
            lambda _: self._settings.set_resolution(self._resolution_combo.currentData())
        )
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._request_stop)
        self._browse_btn.clicked.connect(self._browse_output)
        self._btn_open.clicked.connect(self._open_output)
        self._eye_btn.toggled.connect(self._toggle_api_visibility)
        # New signal connections
        self._local_model_check.toggled.connect(self._on_local_model_toggled)
        self._local_model_check.toggled.connect(
            lambda v: self._settings.set_use_local_model(v)
        )
        self._model_url_edit.textChanged.connect(
            lambda t: self._settings.set_local_model_url(t)
        )
        self._model_url_edit.textChanged.connect(lambda _: self._validate())
        self._model_name_edit.textChanged.connect(
            lambda t: self._settings.set_model_name(t)
        )
        self._blur_spin.valueChanged.connect(
            lambda v: self._settings.set_blur_threshold(v)
        )
        self._system_prompt_edit.textChanged.connect(
            lambda: self._settings.set_custom_system_prompt(
                self._system_prompt_edit.toPlainText()
            )
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate(self) -> None:
        url_text = self._url_edit.toPlainText().strip()
        key = self._api_edit.text().strip()
        use_local = self._local_model_check.isChecked()
        errors: list[str] = []

        # Validate URLs — at least one valid URL required
        if not url_text:
            errors.append(self.tr("URL required"))
        else:
            urls = [u.strip() for u in url_text.splitlines() if u.strip()]
            for u in urls:
                if not u.startswith("http"):
                    errors.append(self.tr("Invalid URL") + f": {u[:30]}")
                    break

        # API key validation depends on mode
        if use_local:
            model_url = self._model_url_edit.text().strip()
            if not model_url:
                errors.append(self.tr("Model API URL required"))
        else:
            if not key:
                errors.append(self.tr("API key required"))
            elif not key.startswith("sk-"):
                errors.append(self.tr("API Key must start with sk-"))

        if errors:
            self._error_label.setText("⚠  " + "  ·  ".join(errors))
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
    # Slots
    # ------------------------------------------------------------------
    def _toggle_api_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._api_edit.setEchoMode(mode)
        self._eye_btn.setText("🙈" if checked else "👁")

    def _on_start(self) -> None:
        url_text = self._url_edit.toPlainText().strip()
        urls = [u.strip() for u in url_text.splitlines() if u.strip()]
        if not urls:
            return

        # Emit one config per URL (MainWindow will handle the batch)
        for url in urls:
            config = JobConfig(
                url=url,
                interval_sec=self._interval_spin.value(),
                api_key=self._api_edit.text().strip(),
                output_dir=Path(self._output_edit.text()),
                prompt_type=self._prompt_combo.currentData(),
                max_frames=self._max_frames_spin.value(),
                resolution=self._resolution_combo.currentData(),
                use_local_model=self._local_model_check.isChecked(),
                local_model_url=self._model_url_edit.text().strip(),
                model_name=self._model_name_edit.text().strip(),
                custom_system_prompt=self._system_prompt_edit.toPlainText().strip(),
                blur_threshold=self._blur_spin.value(),
            )
            self._settings.sync()
            self.job_requested.emit(config)

    def _on_language_changed(self) -> None:
        code: str = self._lang_combo.currentData()
        self._settings.set_language(code)
        QMessageBox.information(
            self,
            self.tr("Language"),
            self.tr("Restart to apply language"),
        )

    def _on_theme_changed(self) -> None:
        theme: str = self._theme_combo.currentData()
        self._settings.set_theme(theme)
        QMessageBox.information(
            self,
            self.tr("Theme"),
            self.tr("Restart to apply theme"),
        )

    def _request_stop(self) -> None:
        self._btn_stop.setEnabled(False)

    def _on_local_model_toggled(self, checked: bool) -> None:
        self._model_url_edit.setEnabled(checked)
        self._model_name_edit.setEnabled(checked)
        self._validate()

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select output folder"), self._output_edit.text()
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

    # ------------------------------------------------------------------
    # Drag & drop URL
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
            self._url_edit.setPlainText(text)
            event.acceptProposedAction()
        else:
            event.ignore()
