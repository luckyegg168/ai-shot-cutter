"""GalleryWidget — scrollable grid of FrameCards."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from core.models import FrameResult
from ui.frame_card import FrameCard

_COLS = 3


class GalleryWidget(QScrollArea):
    """Scrollable grid of FrameCard widgets.

    Emits ``card_selected(FrameResult)`` when the user clicks a card.
    """

    card_selected = Signal(object)   # FrameResult

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: list[FrameCard] = []
        self._selected_card: FrameCard | None = None
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setSpacing(8)
        self.setWidget(self._container)

    # ------------------------------------------------------------------
    def add_frame_card(self, frame_result: FrameResult) -> None:
        """Append a new FrameCard and auto-scroll to it."""
        card = FrameCard(frame_result)
        card.selected.connect(self._on_card_selected)

        row, col = divmod(len(self._cards), _COLS)
        self._grid.addWidget(card, row, col)
        self._cards.append(card)

        # Auto-scroll to newest card
        self._container.adjustSize()
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self) -> None:
        """Remove all cards."""
        for card in self._cards:
            self._grid.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._selected_card = None

    # ------------------------------------------------------------------
    def _on_card_selected(self, result: FrameResult) -> None:
        # Deselect previous
        if self._selected_card is not None:
            self._selected_card.set_selected(False)

        # Find and select new
        for card in self._cards:
            if card.frame_result is result:
                card.set_selected(True)
                self._selected_card = card
                break

        self.card_selected.emit(result)
