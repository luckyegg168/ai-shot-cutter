"""GalleryWidget — scrollable grid of FrameCards with adjustable columns."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.models import FrameResult
from ui.frame_card import FrameCard

_DEFAULT_COLS = 3
_COL_OPTIONS = [2, 3, 4, 6]


class GalleryWidget(QWidget):
    """Scrollable grid of FrameCard widgets with adjustable columns.

    Emits ``card_selected(FrameResult)`` when the user clicks a card.
    """

    card_selected = Signal(object)   # FrameResult

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: list[FrameCard] = []
        self._selected_card: FrameCard | None = None
        self._selected_index: int = -1
        self._cols = _DEFAULT_COLS
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        # ── Toolbar row: column selector ─────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 6, 10, 0)
        toolbar.addWidget(QLabel(self.tr("欄位數")))
        self._col_combo = QComboBox()
        self._col_combo.setFixedWidth(60)
        for n in _COL_OPTIONS:
            self._col_combo.addItem(str(n), n)
        idx = _COL_OPTIONS.index(_DEFAULT_COLS) if _DEFAULT_COLS in _COL_OPTIONS else 0
        self._col_combo.setCurrentIndex(idx)
        self._col_combo.currentIndexChanged.connect(self._on_cols_changed)
        toolbar.addWidget(self._col_combo)
        toolbar.addStretch()
        self._counter_label = QLabel("0 影格")
        self._counter_label.setStyleSheet("color: #7f849c; font-size: 11px;")
        toolbar.addWidget(self._counter_label)
        outer.addLayout(toolbar)

        # ── Scroll area ──────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setSpacing(12)
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    # ------------------------------------------------------------------
    # Feature: adjustable gallery columns
    # ------------------------------------------------------------------
    def _on_cols_changed(self) -> None:
        self._cols = self._col_combo.currentData()
        self._relayout()

    def _relayout(self) -> None:
        """Re-place all cards in the grid with current column count."""
        for card in self._cards:
            self._grid.removeWidget(card)
        for i, card in enumerate(self._cards):
            row, col = divmod(i, self._cols)
            self._grid.addWidget(card, row, col)

    # ------------------------------------------------------------------
    # Feature: frame navigation (← →)
    # ------------------------------------------------------------------
    def select_prev(self) -> None:
        """Select the previous card."""
        if not self._cards:
            return
        idx = max(0, self._selected_index - 1)
        self._select_by_index(idx)

    def select_next(self) -> None:
        """Select the next card."""
        if not self._cards:
            return
        idx = min(len(self._cards) - 1, self._selected_index + 1)
        self._select_by_index(idx)

    def _select_by_index(self, idx: int) -> None:
        if 0 <= idx < len(self._cards):
            card = self._cards[idx]
            card.selected.emit(card.frame_result)

    # ------------------------------------------------------------------
    def add_frame_card(self, frame_result: FrameResult) -> None:
        """Append a new FrameCard and auto-scroll to it."""
        card = FrameCard(frame_result)
        card.selected.connect(self._on_card_selected)

        row, col = divmod(len(self._cards), self._cols)
        self._grid.addWidget(card, row, col)
        self._cards.append(card)
        self._counter_label.setText(f"{len(self._cards)} 影格")

        # Auto-scroll to newest card
        self._container.adjustSize()
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self) -> None:
        """Remove all cards."""
        for card in self._cards:
            self._grid.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._selected_card = None
        self._selected_index = -1
        self._counter_label.setText("0 影格")

    # ------------------------------------------------------------------
    def get_all_frames(self) -> list[FrameResult]:
        """Return all FrameResult objects."""
        return [c.frame_result for c in self._cards]

    # ------------------------------------------------------------------
    def _on_card_selected(self, result: FrameResult) -> None:
        # Deselect previous
        if self._selected_card is not None:
            self._selected_card.set_selected(False)

        # Find and select new
        for i, card in enumerate(self._cards):
            if card.frame_result is result:
                card.set_selected(True)
                self._selected_card = card
                self._selected_index = i
                break

        self.card_selected.emit(result)
