"""Toast — non-blocking overlay notification for the main window.

Usage:
    # In MainWindow.__init__:
    self._toast = Toast(self)

    # Anywhere:
    self._toast.show_message("Copied!", "info")
    self._toast.show_message("Export failed", "error")
"""
from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QRect, QTimer, Qt
from PySide6.QtWidgets import QLabel, QSizePolicy

# level → (text colour, background colour, border colour)
_PALETTE = {
    "info":    ("#a6e3a1", "#1a2e21", "#a6e3a1"),
    "warning": ("#f9e2af", "#2e2a14", "#f9e2af"),
    "error":   ("#f38ba8", "#2e1220", "#f38ba8"),
}


class Toast(QLabel):
    """Floating notification label that auto-dismisses after a few seconds."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setObjectName("toast_widget")
        # Raise above siblings so it renders on top
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade)

        self._anim: QPropertyAnimation | None = None
        self.hide()

    # ------------------------------------------------------------------
    def show_message(
        self,
        message: str,
        level: str = "info",
        duration_ms: int = 2600,
    ) -> None:
        """Display the toast with *message* at the given *level*."""
        fg, bg, border = _PALETTE.get(level, _PALETTE["info"])
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            f"border: 1px solid {border}; border-radius: 8px; "
            "padding: 8px 18px; font-size: 13px; font-weight: 500;"
        )
        self.setText(message)
        self.adjustSize()
        self._reposition()
        # Reset any running fade
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self._timer.stop()
        self._timer.start(duration_ms)

    # ------------------------------------------------------------------
    def _reposition(self) -> None:
        if not self.parent():
            return
        parent_rect: QRect = self.parent().rect()
        w = max(self.sizeHint().width() + 36, 180)
        h = self.sizeHint().height() + 4
        x = parent_rect.width() - w - 18
        y = 44  # below the menu bar
        self.setGeometry(x, y, w, h)

    def _start_fade(self) -> None:
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(450)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.hide)
        self._anim.start()
