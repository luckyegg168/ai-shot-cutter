"""SettingsPanel — dedicated settings page extracted from InputPanel."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from utils.i18n import SUPPORTED_LANGUAGES
from utils.settings import AppSettings

_FIELD_H = 34
_LBL_W = 160


class SettingsPanel(QWidget):
    """Dedicated settings tab — API keys, output, model, theme, language, etc."""

    settings_changed = Signal()  # emitted when any setting changes

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()
        self._load_settings()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(16)

        # ── 1. General Settings ─────────────────────────────────────
        root.addWidget(self._build_general_group())

        # ── 2. API / Model Settings ─────────────────────────────────
        root.addWidget(self._build_api_group())

        # ── 3. Frame Processing ─────────────────────────────────────
        root.addWidget(self._build_processing_group())

        # ── 4. Appearance ───────────────────────────────────────────
        root.addWidget(self._build_appearance_group())

        root.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    # ── Group builders ──────────────────────────────────────────────
    def _build_general_group(self) -> QGroupBox:
        grp = QGroupBox(self.tr("General"))
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        grid.setColumnMinimumWidth(0, _LBL_W)
        grid.setColumnStretch(1, 1)
        lbl = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # Output Dir
        grid.addWidget(self._lbl(self.tr("Output Dir")), 0, 0, lbl)
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
        grid.addWidget(dir_wrap, 0, 1)

        # Video Resolution
        grid.addWidget(self._lbl(self.tr("Video Resolution")), 1, 0, lbl)
        self._resolution_combo = QComboBox()
        self._resolution_combo.setFixedHeight(_FIELD_H)
        self._resolution_combo.addItem("720p", "720")
        self._resolution_combo.addItem("1080p", "1080")
        self._resolution_combo.addItem(self.tr("Best Quality"), "best")
        self._resolution_combo.setToolTip(self.tr("Video resolution limit for yt-dlp"))
        grid.addWidget(self._resolution_combo, 1, 1)

        return grp

    def _build_api_group(self) -> QGroupBox:
        grp = QGroupBox(self.tr("API / Model"))
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        grid.setColumnMinimumWidth(0, _LBL_W)
        grid.setColumnStretch(1, 1)
        lbl = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # OpenAI API Key + eye
        grid.addWidget(self._lbl(self.tr("OpenAI API Key")), 0, 0, lbl)
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
        grid.addWidget(api_wrap, 0, 1)

        # Local Model toggle
        grid.addWidget(self._lbl(self.tr("Local Model")), 1, 0, lbl)
        self._local_model_check = QCheckBox(self.tr("Use Local Model"))
        self._local_model_check.setFixedHeight(_FIELD_H)
        grid.addWidget(self._local_model_check, 1, 1)

        # Model Name
        grid.addWidget(self._lbl(self.tr("Model Name")), 2, 0, lbl)
        self._model_name_edit = QLineEdit()
        self._model_name_edit.setFixedHeight(_FIELD_H)
        self._model_name_edit.setPlaceholderText("gpt-4o / llava / llama3.2-vision")
        self._model_name_edit.setToolTip(self.tr("Model name for API"))
        grid.addWidget(self._model_name_edit, 2, 1)

        # Model API URL
        grid.addWidget(self._lbl(self.tr("Model API URL")), 3, 0, lbl)
        self._model_url_edit = QLineEdit()
        self._model_url_edit.setFixedHeight(_FIELD_H)
        self._model_url_edit.setPlaceholderText("http://192.168.1.100:11434/v1")
        self._model_url_edit.setToolTip(self.tr("OpenAI-compatible API endpoint"))
        grid.addWidget(self._model_url_edit, 3, 1)

        # Custom System Prompt
        grid.addWidget(self._lbl(self.tr("System Prompt")), 4, 0, lbl)
        self._system_prompt_edit = QPlainTextEdit()
        self._system_prompt_edit.setFixedHeight(80)
        self._system_prompt_edit.setPlaceholderText(
            self.tr("Leave empty to use default prompt…")
        )
        self._system_prompt_edit.setToolTip(self.tr("Custom system prompt (overrides default)"))
        grid.addWidget(self._system_prompt_edit, 4, 1)

        return grp

    def _build_processing_group(self) -> QGroupBox:
        grp = QGroupBox(self.tr("Frame Processing"))
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        grid.setColumnMinimumWidth(0, _LBL_W)
        grid.setColumnStretch(1, 1)
        lbl = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # Blur Threshold
        grid.addWidget(self._lbl(self.tr("Blur Threshold")), 0, 0, lbl)
        self._blur_spin = QDoubleSpinBox()
        self._blur_spin.setFixedHeight(_FIELD_H)
        self._blur_spin.setRange(0.0, 9999.0)
        self._blur_spin.setSingleStep(10.0)
        self._blur_spin.setDecimals(1)
        self._blur_spin.setSpecialValueText(self.tr("Disabled"))
        self._blur_spin.setToolTip(self.tr("Skip frames with blur score below this (0=disabled)"))
        grid.addWidget(self._blur_spin, 0, 1)

        return grp

    def _build_appearance_group(self) -> QGroupBox:
        grp = QGroupBox(self.tr("Appearance"))
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        grid.setColumnMinimumWidth(0, _LBL_W)
        grid.setColumnStretch(1, 1)
        lbl = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # Theme
        grid.addWidget(self._lbl(self.tr("Theme")), 0, 0, lbl)
        self._theme_combo = QComboBox()
        self._theme_combo.setFixedHeight(_FIELD_H)
        self._theme_combo.addItem(self.tr("Dark Theme"), "dark")
        self._theme_combo.addItem(self.tr("Light Theme"), "light")
        self._theme_combo.setToolTip(self.tr("Toggle dark / light appearance"))
        grid.addWidget(self._theme_combo, 0, 1)

        # Language
        grid.addWidget(self._lbl(self.tr("Language")), 1, 0, lbl)
        self._lang_combo = QComboBox()
        self._lang_combo.setFixedHeight(_FIELD_H)
        for code, label in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(label, code)
        self._lang_combo.setToolTip(self.tr("Restart to apply language"))
        grid.addWidget(self._lang_combo, 1, 1)

        return grp

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
    # Settings persistence
    # ------------------------------------------------------------------
    def _load_settings(self) -> None:
        s = self._settings
        self._api_edit.setText(s.get_api_key())
        self._output_edit.setText(str(s.get_output_dir()))
        res_idx = self._resolution_combo.findData(s.get_resolution())
        if res_idx >= 0:
            self._resolution_combo.setCurrentIndex(res_idx)
        theme_idx = self._theme_combo.findData(s.get_theme())
        if theme_idx >= 0:
            self._theme_combo.setCurrentIndex(theme_idx)
        lang_idx = self._lang_combo.findData(s.get_language())
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)
        self._local_model_check.setChecked(s.get_use_local_model())
        self._model_url_edit.setText(s.get_local_model_url())
        self._model_name_edit.setText(s.get_model_name())
        self._system_prompt_edit.setPlainText(s.get_custom_system_prompt())
        self._blur_spin.setValue(s.get_blur_threshold())
        self._on_local_model_toggled(s.get_use_local_model())

    def _connect_signals(self) -> None:
        self._api_edit.textChanged.connect(lambda t: self._settings.set_api_key(t))
        self._api_edit.textChanged.connect(lambda _: self.settings_changed.emit())
        self._resolution_combo.currentIndexChanged.connect(
            lambda _: self._settings.set_resolution(self._resolution_combo.currentData())
        )
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self._browse_btn.clicked.connect(self._browse_output)
        self._eye_btn.toggled.connect(self._toggle_api_visibility)
        self._local_model_check.toggled.connect(self._on_local_model_toggled)
        self._local_model_check.toggled.connect(
            lambda v: self._settings.set_use_local_model(v)
        )
        self._model_url_edit.textChanged.connect(
            lambda t: self._settings.set_local_model_url(t)
        )
        self._model_url_edit.textChanged.connect(lambda _: self.settings_changed.emit())
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
    # Slots
    # ------------------------------------------------------------------
    def _toggle_api_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._api_edit.setEchoMode(mode)
        self._eye_btn.setText("🙈" if checked else "👁")

    def _on_local_model_toggled(self, checked: bool) -> None:
        self._model_url_edit.setEnabled(checked)
        self._model_name_edit.setEnabled(checked)
        self.settings_changed.emit()

    def _on_theme_changed(self) -> None:
        theme: str = self._theme_combo.currentData()
        self._settings.set_theme(theme)
        QMessageBox.information(
            self,
            self.tr("Theme"),
            self.tr("Restart to apply theme"),
        )

    def _on_language_changed(self) -> None:
        code: str = self._lang_combo.currentData()
        self._settings.set_language(code)
        QMessageBox.information(
            self,
            self.tr("Language"),
            self.tr("Restart to apply language"),
        )

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select output folder"), self._output_edit.text()
        )
        if folder:
            self._output_edit.setText(folder)
            self._settings.set_output_dir(Path(folder))
            self.settings_changed.emit()

    # ------------------------------------------------------------------
    # Public API: read current settings values for job creation
    # ------------------------------------------------------------------
    def get_api_key(self) -> str:
        return self._api_edit.text().strip()

    def get_output_dir(self) -> Path:
        return Path(self._output_edit.text())

    def get_resolution(self) -> str:
        return self._resolution_combo.currentData()

    def is_local_model(self) -> bool:
        return self._local_model_check.isChecked()

    def get_local_model_url(self) -> str:
        return self._model_url_edit.text().strip()

    def get_model_name(self) -> str:
        return self._model_name_edit.text().strip()

    def get_custom_system_prompt(self) -> str:
        return self._system_prompt_edit.toPlainText().strip()

    def get_blur_threshold(self) -> float:
        return self._blur_spin.value()
