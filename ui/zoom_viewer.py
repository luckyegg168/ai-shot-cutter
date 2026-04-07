"""ZoomViewer — full-size frame popup with zoom/pan."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout

from core.models import FrameResult


class ZoomViewer(QDialog):
    """Modal dialog that shows the full-size frame image with scroll-to-pan."""

    def __init__(self, frame: FrameResult, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            self.tr("Frame %1  ·  %2").replace("%1", str(frame.index)).replace("%2", frame.timestamp_label)
        )
        self.resize(900, 650)
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(str(frame.image_path))
        if not pixmap.isNull():
            self._image_label.setPixmap(pixmap)
        else:
            self._image_label.setText(self.tr("Image not found"))

        scroll.setWidget(self._image_label)
        layout.addWidget(scroll)
