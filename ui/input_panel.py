"""InputPanel — URL, interval, prompt type, max frames, start/stop controls.

Settings (API key, output dir, model, theme, language, etc.) have been moved
to the dedicated SettingsPanel.
"""
from __future__ import annotations


from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import JobConfig
from utils.settings import AppSettings

_FIELD_H = 34   # uniform height for all input widgets
_LBL_W  = 150   # fixed label column width


class InputPanel(QWidget):
    """Job configuration form — simplified to URL + job parameters + start/stop."""

    job_requested = Signal(object)  # JobConfig
    clipboard_url_detected = Signal(str)  # emitted when clipboard contains new YouTube URL

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._settings_panel = None  # set by MainWindow after construction
        self._running = False
        self._last_clipboard_url = ""
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

    def set_settings_panel(self, panel) -> None:
        """Wire the SettingsPanel so InputPanel can read its values at job start."""
        self._settings_panel = panel
        panel.settings_changed.connect(self._validate)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(0)

        # ── Clipboard banner (hidden by default) ──────────────────────
        self._clipboard_banner = QFrame()
        self._clipboard_banner.setObjectName("clipboard_banner")
        self._clipboard_banner.setStyleSheet(
            "#clipboard_banner { background: #1e2030; border: 1px solid #89b4fa;"
            " border-radius: 6px; padding: 4px; }"
        )
        banner_row = QHBoxLayout(self._clipboard_banner)
        banner_row.setContentsMargins(10, 6, 10, 6)
        self._banner_label = QLabel()
        self._banner_label.setStyleSheet("color: #89b4fa; font-size: 12px;")
        self._banner_use_btn = QPushButton(self.tr("Use URL"))
        self._banner_use_btn.setFixedHeight(26)
        self._banner_use_btn.setObjectName("btn_start")
        self._banner_dismiss_btn = QPushButton("✕")
        self._banner_dismiss_btn.setFixedSize(26, 26)
        banner_row.addWidget(self._banner_label)
        banner_row.addStretch()
        banner_row.addWidget(self._banner_use_btn)
        banner_row.addSpacing(4)
        banner_row.addWidget(self._banner_dismiss_btn)
        self._clipboard_banner.setVisible(False)
        root.addWidget(self._clipboard_banner)
        root.addSpacing(8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnMinimumWidth(0, _LBL_W)
        grid.setColumnMinimumWidth(2, _LBL_W)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        lbl = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # Row 0 ── Recent URLs dropdown + YouTube URL (multi-line for batch)
        grid.addWidget(self._lbl("YouTube URL"), 0, 0, lbl)
        url_col = QVBoxLayout()
        url_col.setSpacing(4)
        # Recent URLs dropdown
        self._recent_combo = QComboBox()
        self._recent_combo.setFixedHeight(28)
        self._recent_combo.setToolTip(self.tr("Recent URLs"))
        self._recent_combo.addItem(self.tr("— Recent URLs —"), "")
        url_col.addWidget(self._recent_combo)
        # Main URL text area
        self._url_edit = QPlainTextEdit()
        self._url_edit.setFixedHeight(72)
        self._url_edit.setPlaceholderText(
            "https://www.youtube.com/watch?v=…\n"
            "(one URL per line for batch processing)"
        )
        self._url_edit.setToolTip(self.tr("YouTube video URL"))
        url_col.addWidget(self._url_edit)
        url_widget = QWidget()
        url_widget.setLayout(url_col)
        grid.addWidget(url_widget, 0, 1, 1, 3)

        # Row 1 ── Interval  |  Prompt Type
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
        self._prompt_combo.addItem(self.tr("Character"), "character")
        self._prompt_combo.addItem(self.tr("Landscape"), "landscape")
        self._prompt_combo.addItem(self.tr("Product"), "product")
        self._prompt_combo.addItem(self.tr("Architecture"), "architecture")
        self._prompt_combo.setMinimumWidth(140)
        grid.addWidget(self._prompt_combo, 1, 3)

        # Row 2 ── Max Frames
        grid.addWidget(self._lbl(self.tr("Max Frames (0=unlimited)")), 2, 0, lbl)
        self._max_frames_spin = QSpinBox()
        self._max_frames_spin.setFixedHeight(_FIELD_H)
        self._max_frames_spin.setRange(0, 500)
        self._max_frames_spin.setSpecialValueText(self.tr("Unlimited"))
        self._max_frames_spin.setToolTip(self.tr("0 = unlimited"))
        grid.addWidget(self._max_frames_spin, 2, 1)

        root.addLayout(grid)
        root.addSpacing(20)

        # ── Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)
        root.addSpacing(12)

        # ── Buttons row
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

        # ── Validation message
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
        self._interval_spin.setValue(s.get_interval())
        self._max_frames_spin.setValue(s.get_max_frames())
        idx = self._prompt_combo.findData(s.get_prompt_type())
        if idx >= 0:
            self._prompt_combo.setCurrentIndex(idx)
        # Populate recent URLs
        self._refresh_recent_urls()

    def _refresh_recent_urls(self) -> None:
        """Reload the recent URLs combo from settings."""
        self._recent_combo.blockSignals(True)
        self._recent_combo.clear()
        self._recent_combo.addItem(self.tr("— Recent URLs —"), "")
        for url in self._settings.get_recent_urls():
            short = url if len(url) <= 60 else url[:57] + "…"
            self._recent_combo.addItem(short, url)
        self._recent_combo.setCurrentIndex(0)
        self._recent_combo.blockSignals(False)

    def _connect_signals(self) -> None:
        self._url_edit.textChanged.connect(self._validate)
        self._interval_spin.valueChanged.connect(lambda v: self._settings.set_interval(v))
        self._max_frames_spin.valueChanged.connect(lambda v: self._settings.set_max_frames(v))
        self._prompt_combo.currentIndexChanged.connect(
            lambda _: self._settings.set_prompt_type(self._prompt_combo.currentData())
        )
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._request_stop)
        self._btn_open.clicked.connect(self._open_output)
        # Recent URLs
        self._recent_combo.currentIndexChanged.connect(self._on_recent_selected)
        # Clipboard banner
        self._banner_use_btn.clicked.connect(self._on_banner_use)
        self._banner_dismiss_btn.clicked.connect(self._clipboard_banner.hide)

    # ------------------------------------------------------------------
    # Clipboard banner (F-18)
    # ------------------------------------------------------------------
    def show_clipboard_banner(self, url: str) -> None:
        """Show the clipboard detection banner with the detected URL."""
        if url == self._last_clipboard_url and self._clipboard_banner.isVisible():
            return
        self._last_clipboard_url = url
        short = url if len(url) <= 70 else url[:67] + "…"
        self._banner_label.setText("📋  " + self.tr("Clipboard:") + " " + short)
        self._clipboard_banner.setVisible(True)

    def hide_clipboard_banner(self) -> None:
        self._clipboard_banner.setVisible(False)

    def _on_banner_use(self) -> None:
        self._url_edit.setPlainText(self._last_clipboard_url)
        self._clipboard_banner.setVisible(False)

    # ------------------------------------------------------------------
    # Recent URLs
    # ------------------------------------------------------------------
    def _on_recent_selected(self, idx: int) -> None:
        url = self._recent_combo.currentData()
        if url:
            self._url_edit.setPlainText(url)
            self._recent_combo.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate(self) -> None:
        url_text = self._url_edit.toPlainText().strip()
        errors: list[str] = []

        if not url_text:
            errors.append(self.tr("URL required"))
        else:
            urls = [u.strip() for u in url_text.splitlines() if u.strip()]
            for u in urls:
                if not u.startswith("http"):
                    errors.append(self.tr("Invalid URL") + f": {u[:30]}")
                    break

        # Validate API key from settings panel (or from AppSettings if panel not wired yet)
        sp = self._settings_panel
        if sp:
            use_local = sp.is_local_model()
            if use_local:
                if not sp.get_local_model_url():
                    errors.append(self.tr("Model API URL required"))
            else:
                key = sp.get_api_key()
                if not key:
                    errors.append(self.tr("API key required"))
                elif not key.startswith("sk-"):
                    errors.append(self.tr("API Key must start with sk-"))
        else:
            # Fallback to saved settings (during init before panel is wired)
            use_local = self._settings.get_use_local_model()
            if use_local:
                if not self._settings.get_local_model_url():
                    errors.append(self.tr("Model API URL required"))
            else:
                key = self._settings.get_api_key()
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
    def _on_start(self) -> None:
        url_text = self._url_edit.toPlainText().strip()
        urls = [u.strip() for u in url_text.splitlines() if u.strip()]
        if not urls:
            return

        # Save each URL to recent history
        for url in urls:
            self._settings.add_recent_url(url)
        self._refresh_recent_urls()

        # Read settings from SettingsPanel (or fallback to AppSettings)
        sp = self._settings_panel
        if sp:
            api_key = sp.get_api_key()
            output_dir = sp.get_output_dir()
            resolution = sp.get_resolution()
            use_local = sp.is_local_model()
            local_url = sp.get_local_model_url()
            model_name = sp.get_model_name()
            system_prompt = sp.get_custom_system_prompt()
            blur_threshold = sp.get_blur_threshold()
        else:
            s = self._settings
            api_key = s.get_api_key()
            output_dir = s.get_output_dir()
            resolution = s.get_resolution()
            use_local = s.get_use_local_model()
            local_url = s.get_local_model_url()
            model_name = s.get_model_name()
            system_prompt = s.get_custom_system_prompt()
            blur_threshold = s.get_blur_threshold()

        for url in urls:
            config = JobConfig(
                url=url,
                interval_sec=self._interval_spin.value(),
                api_key=api_key,
                output_dir=output_dir,
                prompt_type=self._prompt_combo.currentData(),
                max_frames=self._max_frames_spin.value(),
                resolution=resolution,
                use_local_model=use_local,
                local_model_url=local_url,
                model_name=model_name,
                custom_system_prompt=system_prompt,
                blur_threshold=blur_threshold,
            )
            self._settings.sync()
            self.job_requested.emit(config)

    def _request_stop(self) -> None:
        self._btn_stop.setEnabled(False)

    def _open_output(self) -> None:
        import subprocess
        import sys

        sp = self._settings_panel
        path = str(sp.get_output_dir()) if sp else str(self._settings.get_output_dir())
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

