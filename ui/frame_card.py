"""FrameCard — thumbnail widget shown in GalleryWidget."""
from __future__ import annotations


from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout

from core.models import FrameResult


class FrameCard(QFrame):
    """Fixed-size card showing a thumbnail, prompt preview, and timestamp."""

    CARD_W = 220
    CARD_H = 195
    THUMB_W = 196
    THUMB_H = 110

    selected = Signal(object)       # FrameResult
    double_clicked = Signal(object)  # FrameResult

    def __init__(self, frame_result: FrameResult, parent=None) -> None:
        super().__init__(parent)
        self._result = frame_result
        self._is_selected = False

        self.setObjectName("frame_card")
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        self._setup_ui()
        self._update_selection_style()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(5)

        # Thumbnail
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(self.THUMB_W, self.THUMB_H)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(self._result.image_path))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                self.THUMB_W, self.THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._thumb_label.setPixmap(pixmap)
        layout.addWidget(self._thumb_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Prompt preview
        preview = self._result.prompt[:80]
        if len(self._result.prompt) > 80:
            preview += "…"
        self._preview_label = QLabel(preview)
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("font-size: 10px; color: #a6adc8;")
        self._preview_label.setFixedWidth(self.THUMB_W)
        layout.addWidget(self._preview_label)

        # Timestamp
        self._ts_label = QLabel(self._result.timestamp_label)
        self._ts_label.setStyleSheet("font-size: 10px; color: #89b4fa; font-weight: 600; letter-spacing: 0.3px;")
        self._ts_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self._ts_label)

    # ------------------------------------------------------------------
    def _update_selection_style(self) -> None:
        self.setProperty("selected", "true" if self._is_selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._update_selection_style()

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self._result)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit(self._result)
        super().mouseDoubleClickEvent(event)

    @property
    def frame_result(self) -> FrameResult:
        return self._result
