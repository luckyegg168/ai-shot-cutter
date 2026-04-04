"""PromptPanel — shows full prompt text for a selected frame."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import FrameResult


class PromptPanel(QWidget):
    """Right panel: shows selected frame image + full prompt text."""

    regenerate_requested = Signal(object)   # FrameResult

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_result: FrameResult | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        group = QGroupBox(self.tr("Selected Frame"))
        inner = QVBoxLayout(group)

        # Header
        self._header_label = QLabel(self.tr("No frame selected"))
        self._header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        inner.addWidget(self._header_label)

        # Preview image
        self._image_label = QLabel()
        self._image_label.setFixedSize(400, 225)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background-color: #181825; border-radius: 4px;")
        inner.addWidget(self._image_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Prompt text
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setReadOnly(True)
        self._prompt_edit.setPlaceholderText(self.tr("Select a frame from the gallery…"))
        inner.addWidget(self._prompt_edit)

        # Buttons
        btn_row = QHBoxLayout()
        self._copy_btn = QPushButton(self.tr("Copy Prompt"))
        self._regen_btn = QPushButton(self.tr("Regenerate"))
        self._copy_btn.setEnabled(False)
        self._regen_btn.setEnabled(False)
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._regen_btn)
        btn_row.addStretch()
        inner.addLayout(btn_row)

        layout.addWidget(group)

        # Connections
        self._copy_btn.clicked.connect(self._copy_prompt)
        self._regen_btn.clicked.connect(self._request_regen)

    # ------------------------------------------------------------------
    def show_frame(self, result: FrameResult) -> None:
        """Display a frame result."""
        self._current_result = result

        self._header_label.setText(
            self.tr(f"Frame {result.index}  ·  {result.timestamp_label}")
        )

        pixmap = QPixmap(str(result.image_path))
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                400, 225,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)
        else:
            self._image_label.clear()
            self._image_label.setText(self.tr("Image not found"))

        self._prompt_edit.setPlainText(result.prompt)
        self._copy_btn.setEnabled(True)
        self._regen_btn.setEnabled(True)

    def update_prompt(self, result: FrameResult) -> None:
        """Update prompt text for current frame (after regeneration)."""
        if self._current_result and self._current_result.index == result.index:
            self._current_result = result
            self._prompt_edit.setPlainText(result.prompt)

    # ------------------------------------------------------------------
    def _copy_prompt(self) -> None:
        text = self._prompt_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _request_regen(self) -> None:
        if self._current_result:
            self.regenerate_requested.emit(self._current_result)
