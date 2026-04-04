"""LogPanel — progress bar + timestamped log output."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    """Bottom panel: progress bar and scrolling log."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)

        group = QGroupBox(self.tr("Progress & Log"))
        inner = QVBoxLayout(group)

        # Progress row
        prog_row = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_label = QLabel("0 / 0")
        self._progress_label.setFixedWidth(60)
        prog_row.addWidget(self._progress_bar)
        prog_row.addWidget(self._progress_label)
        inner.addLayout(prog_row)

        # Log text area
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumHeight(140)
        inner.addWidget(self._log_edit)

        # Clear button
        self._clear_btn = QPushButton(self.tr("Clear Log"))
        self._clear_btn.setFixedWidth(90)
        self._clear_btn.clicked.connect(self._log_edit.clear)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._clear_btn)
        inner.addLayout(btn_row)

        layout.addWidget(group)

    # ------------------------------------------------------------------
    def set_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            pct = int(current / total * 100)
        else:
            pct = 0
        self._progress_bar.setValue(pct)
        self._progress_label.setText(f"{current} / {total}")
        if message:
            self.log_info(message)

    def reset_progress(self) -> None:
        self._progress_bar.setValue(0)
        self._progress_label.setText("0 / 0")

    # ------------------------------------------------------------------
    def log_info(self, text: str) -> None:
        self._append(text, "#a6e3a1")

    def log_warning(self, text: str) -> None:
        self._append(text, "#f9e2af")

    def log_error(self, text: str) -> None:
        self._append(text, "#f38ba8")

    def _append(self, text: str, color: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        cursor = self._log_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._log_edit.setTextCursor(cursor)
        self._log_edit.setTextColor(QColor(color))
        self._log_edit.insertPlainText(f"[{ts}] {text}\n")
        # Auto-scroll
        sb = self._log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
