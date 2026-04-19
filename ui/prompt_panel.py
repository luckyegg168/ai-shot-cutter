"""PromptPanel — shows full prompt text for a selected frame + batch actions."""
from __future__ import annotations

from pathlib import Path

import shutil

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
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
        self._all_frames_getter = None  # callable returning list[FrameResult]
        self._setup_ui()

    def set_all_frames_getter(self, getter) -> None:
        """Register a callable that returns all FrameResult objects."""
        self._all_frames_getter = getter

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        group = QGroupBox(self.tr("Selected Frame"))
        inner = QVBoxLayout(group)
        inner.setSpacing(10)

        # Header
        self._header_label = QLabel(self.tr("No frame selected"))
        self._header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        inner.addWidget(self._header_label)

        # Preview image
        self._image_label = QLabel()
        self._image_label.setFixedSize(400, 225)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background-color: #181825; border-radius: 6px;")
        inner.addWidget(self._image_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        inner.addSpacing(4)

        # Prompt text
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setReadOnly(True)
        self._prompt_edit.setPlaceholderText(self.tr("Select a frame from the gallery..."))
        inner.addWidget(self._prompt_edit)

        # Char/word counter  (v1.3 F-19)
        self._counter_label = QLabel("0 chars · 0 words")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._counter_label.setStyleSheet("font-size: 10px; color: #7f849c;")
        inner.addWidget(self._counter_label)
        self._prompt_edit.textChanged.connect(self._update_counter)

        # Single-frame buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._copy_btn = QPushButton(self.tr("Copy Prompt"))
        self._regen_btn = QPushButton(self.tr("Regenerate"))
        self._save_btn = QPushButton(self.tr("Save Frame"))
        self._save_btn.setToolTip(self.tr("Save this frame image to disk"))
        self._copy_btn.setEnabled(False)
        self._regen_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._regen_btn)
        btn_row.addWidget(self._save_btn)
        btn_row.addStretch()
        inner.addLayout(btn_row)

        inner.addSpacing(8)

        # ── Batch action buttons ───────────────────────────────────
        batch_row = QHBoxLayout()
        batch_row.setSpacing(8)
        self._copy_all_btn = QPushButton(self.tr("Copy All Prompts"))
        self._copy_all_btn.setToolTip(self.tr("Copy all frame prompts to clipboard"))
        self._export_btn = QPushButton(self.tr("Export Prompts (.txt)"))
        self._export_btn.setToolTip(self.tr("Export all prompts to a .txt file"))
        self._save_all_btn = QPushButton(self.tr("Save All Frames"))
        self._save_all_btn.setToolTip(self.tr("Save all frame images to a folder"))
        batch_row.addWidget(self._copy_all_btn)
        batch_row.addWidget(self._export_btn)
        batch_row.addWidget(self._save_all_btn)
        batch_row.addStretch()
        inner.addLayout(batch_row)

        layout.addWidget(group)

        # Connections
        self._copy_btn.clicked.connect(self._copy_prompt)
        self._regen_btn.clicked.connect(self._request_regen)
        self._save_btn.clicked.connect(self._save_frame)
        self._copy_all_btn.clicked.connect(self._copy_all_prompts)
        self._export_btn.clicked.connect(self._export_all_prompts)
        self._save_all_btn.clicked.connect(self._save_all_frames)

    # ------------------------------------------------------------------
    def _update_counter(self) -> None:
        text = self._prompt_edit.toPlainText()
        chars = len(text)
        words = len(text.split()) if text.strip() else 0
        self._counter_label.setText(
            self.tr("%1 chars · %2 words").replace("%1", str(chars)).replace("%2", str(words))
        )

    # ------------------------------------------------------------------
    def show_frame(self, result: FrameResult) -> None:
        """Display a frame result."""
        self._current_result = result

        self._header_label.setText(
            self.tr("Frame %1  ·  %2").replace("%1", str(result.index)).replace("%2", result.timestamp_label)
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
        self._save_btn.setEnabled(True)

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

    def _save_frame(self) -> None:
        """Save the currently selected frame image to a user-chosen path."""
        if not self._current_result:
            return
        src = self._current_result.image_path
        default_name = src.name
        dest, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Frame"),
            default_name,
            "Images (*.jpg *.jpeg *.png *.webp);;All Files (*)",
        )
        if not dest:
            return
        shutil.copy2(src, dest)
        QMessageBox.information(
            self,
            self.tr("Saved"),
            self.tr("Frame saved to:\n%1").replace("%1", dest),
        )

    # ------------------------------------------------------------------
    # Feature 1: Copy All Prompts
    # ------------------------------------------------------------------
    def _copy_all_prompts(self) -> None:
        frames = self._get_all_frames()
        if not frames:
            return
        text = self._build_prompts_text(frames)
        QApplication.clipboard().setText(text)
        QMessageBox.information(
            self,
            self.tr("Copied"),
            self.tr("Copied %1 prompts to clipboard.").replace("%1", str(len(frames))),
        )

    # ------------------------------------------------------------------
    # Feature 2: Export All Prompts
    # ------------------------------------------------------------------
    def _export_all_prompts(self) -> None:
        frames = self._get_all_frames()
        if not frames:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export All Prompts"),
            "all_prompts.txt",
            "Text Files (*.txt)",
        )
        if not path:
            return

        text = self._build_prompts_text(frames)
        Path(path).write_text(text, encoding="utf-8")
        QMessageBox.information(
            self,
            self.tr("Export Complete"),
            self.tr("Exported %1 prompts to:\n%2").replace("%1", str(len(frames))).replace("%2", path),
        )

    # ------------------------------------------------------------------
    # Save All Frames
    # ------------------------------------------------------------------
    def _save_all_frames(self) -> None:
        """Copy all frame images to a user-chosen folder."""
        frames = self._get_all_frames()
        if not frames:
            QMessageBox.warning(
                self,
                self.tr("No Frames"),
                self.tr("No frames available to save."),
            )
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select folder to save frames"),
        )
        if not folder:
            return

        dest_dir = Path(folder)
        saved = 0
        for fr in frames:
            dest = dest_dir / fr.image_path.name
            shutil.copy2(fr.image_path, dest)
            saved += 1

        QMessageBox.information(
            self,
            self.tr("Saved"),
            self.tr("Saved %1 frames to:\n%2").replace("%1", str(saved)).replace("%2", folder),
        )

    # ------------------------------------------------------------------
    def _get_all_frames(self) -> list[FrameResult]:
        if self._all_frames_getter:
            return self._all_frames_getter()
        return []

    @staticmethod
    def _build_prompts_text(frames: list[FrameResult]) -> str:
        parts: list[str] = []
        for f in frames:
            parts.append(f"--- Frame {f.index} | {f.timestamp_label} ---")
            parts.append(f.prompt)
            parts.append("")
        return "\n".join(parts)
