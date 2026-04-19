"""GalleryWidget — scrollable grid of FrameCards with adjustable columns."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import FrameResult
from ui.frame_card import FrameCard

_DEFAULT_COLS = 3
_COL_OPTIONS = [2, 3, 4, 6]

_SORT_OPTIONS = [
    ("Frame Order", "index"),
    ("Timestamp ▲", "ts_asc"),
    ("Timestamp ▼", "ts_desc"),
    ("Prompt Length", "prompt_len"),
]


class GalleryWidget(QWidget):
    """Scrollable grid of FrameCard widgets with adjustable columns.

    Emits ``card_selected(FrameResult)`` when the user clicks a card.
    """

    card_selected = Signal(object)        # FrameResult
    card_double_clicked = Signal(object)  # FrameResult

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: list[FrameCard] = []
        self._selected_card: FrameCard | None = None
        self._selected_index: int = -1
        self._cols = _DEFAULT_COLS
        self._starred_only = False
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        # ── Toolbar row ───────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 6, 10, 0)

        # Column selector
        toolbar.addWidget(QLabel(self.tr("Cols")))
        self._col_combo = QComboBox()
        self._col_combo.setFixedWidth(52)
        for n in _COL_OPTIONS:
            self._col_combo.addItem(str(n), n)
        idx = _COL_OPTIONS.index(_DEFAULT_COLS) if _DEFAULT_COLS in _COL_OPTIONS else 0
        self._col_combo.setCurrentIndex(idx)
        self._col_combo.currentIndexChanged.connect(self._on_cols_changed)
        toolbar.addWidget(self._col_combo)
        toolbar.addSpacing(10)

        # Sort selector
        toolbar.addWidget(QLabel(self.tr("Sort")))
        self._sort_combo = QComboBox()
        self._sort_combo.setFixedWidth(130)
        for label, key in _SORT_OPTIONS:
            self._sort_combo.addItem(self.tr(label), key)
        self._sort_combo.currentIndexChanged.connect(self._apply_sort)
        toolbar.addWidget(self._sort_combo)
        toolbar.addSpacing(10)

        # Starred filter
        self._starred_check = QCheckBox("⭐")
        self._starred_check.setToolTip(self.tr("Show favorites only"))
        self._starred_check.toggled.connect(self._on_starred_filter)
        toolbar.addWidget(self._starred_check)

        toolbar.addStretch()

        # Frame jump (enter frame number)
        self._jump_spin = QSpinBox()
        self._jump_spin.setFixedWidth(62)
        self._jump_spin.setMinimum(1)
        self._jump_spin.setMaximum(9999)
        self._jump_spin.setPrefix("#")
        self._jump_spin.setToolTip(self.tr("Jump to frame number"))
        self._jump_spin.editingFinished.connect(self._jump_to_frame)
        toolbar.addWidget(self._jump_spin)
        toolbar.addSpacing(8)

        # Filter edit
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText(self.tr("Filter prompts…"))
        self._filter_edit.setFixedWidth(170)
        self._filter_edit.setClearButtonEnabled(True)
        self._filter_edit.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._filter_edit)
        toolbar.addSpacing(8)

        self._counter_label = QLabel(self.tr("%1 frames").replace("%1", "0"))
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

        # ── Empty state label (shown when no cards) ─────────────────
        self._empty_label = QLabel(
            "🎞  " + self.tr("No frames yet") + "\n\n"
            + self.tr("Paste a YouTube URL in the Job Settings tab and press Start.")
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #45475a; font-size: 14px; background: transparent;"
        )
        self._empty_label.setWordWrap(True)
        outer.addWidget(self._empty_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setVisible(True)
        self._scroll.setVisible(False)

    # ------------------------------------------------------------------
    # Feature: adjustable gallery columns
    # ------------------------------------------------------------------
    def _on_cols_changed(self) -> None:
        self._cols = self._col_combo.currentData()
        self._relayout()

    def _relayout(self) -> None:
        """Re-place all *visible* cards in the grid with current column count."""
        for card in self._cards:
            self._grid.removeWidget(card)
        visible_cards = [c for c in self._cards if c.isVisible()]
        for i, card in enumerate(visible_cards):
            row, col = divmod(i, self._cols)
            self._grid.addWidget(card, row, col)

    # ------------------------------------------------------------------
    # Feature: Gallery Sort
    # ------------------------------------------------------------------
    def _apply_sort(self) -> None:
        key = self._sort_combo.currentData()
        if key == "index":
            self._cards.sort(key=lambda c: c.frame_result.index)
        elif key == "ts_asc":
            self._cards.sort(key=lambda c: c.frame_result.timestamp_sec)
        elif key == "ts_desc":
            self._cards.sort(key=lambda c: -c.frame_result.timestamp_sec)
        elif key == "prompt_len":
            self._cards.sort(key=lambda c: -len(c.frame_result.prompt))
        self._relayout()

    # ------------------------------------------------------------------
    # Feature: Starred-only filter
    # ------------------------------------------------------------------
    def _on_starred_filter(self, checked: bool) -> None:
        self._starred_only = checked
        self._apply_visibility()

    def _apply_visibility(self) -> None:
        """Apply both text filter and starred filter."""
        needle = self._filter_edit.text().strip().lower()
        visible = 0
        for card in self._cards:
            text_ok = not needle or needle in card.frame_result.prompt.lower()
            star_ok = not self._starred_only or card.is_favorite
            show = text_ok and star_ok
            card.setVisible(show)
            if show:
                visible += 1
        self._counter_label.setText(
            self.tr("%1 frames").replace("%1", str(visible))
        )
        self._relayout()

    # ------------------------------------------------------------------
    # Feature: frame navigation (← →)
    # ------------------------------------------------------------------
    def select_prev(self) -> None:
        if not self._cards:
            return
        idx = max(0, self._selected_index - 1)
        self._select_by_index(idx)

    def select_next(self) -> None:
        if not self._cards:
            return
        idx = min(len(self._cards) - 1, self._selected_index + 1)
        self._select_by_index(idx)

    def select_first(self) -> None:
        if self._cards:
            self._select_by_index(0)

    def select_last(self) -> None:
        if self._cards:
            self._select_by_index(len(self._cards) - 1)

    def _select_by_index(self, idx: int) -> None:
        if 0 <= idx < len(self._cards):
            card = self._cards[idx]
            card.selected.emit(card.frame_result)

    # ------------------------------------------------------------------
    # Feature: jump to frame number
    # ------------------------------------------------------------------
    def _jump_to_frame(self) -> None:
        target = self._jump_spin.value()
        for i, card in enumerate(self._cards):
            if card.frame_result.index == target:
                self._select_by_index(i)
                # Scroll to the card
                self._scroll.ensureWidgetVisible(card)
                return

    # ------------------------------------------------------------------
    def add_frame_card(self, frame_result: FrameResult) -> None:
        """Append a new FrameCard and auto-scroll to it."""
        card = FrameCard(frame_result)
        card.selected.connect(self._on_card_selected)
        card.double_clicked.connect(lambda fr: self.card_double_clicked.emit(fr))

        row, col = divmod(len(self._cards), self._cols)
        self._grid.addWidget(card, row, col)
        self._cards.append(card)
        self._counter_label.setText(self.tr("%1 frames").replace("%1", str(len(self._cards))))

        # Show scroll area and hide empty state
        if len(self._cards) == 1:
            self._empty_label.setVisible(False)
            self._scroll.setVisible(True)
            self._jump_spin.setMaximum(1)

        self._jump_spin.setMaximum(len(self._cards))

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
        self._counter_label.setText(self.tr("%1 frames").replace("%1", "0"))
        self._jump_spin.setMinimum(1)
        self._jump_spin.setMaximum(1)
        self._jump_spin.setValue(1)
        self._empty_label.setVisible(True)
        self._scroll.setVisible(False)

    # ------------------------------------------------------------------
    def get_all_frames(self) -> list[FrameResult]:
        """Return all FrameResult objects."""
        return [c.frame_result for c in self._cards]

    def get_favorite_frames(self) -> list[FrameResult]:
        """Return only favorited FrameResult objects."""
        return [c.frame_result for c in self._cards if c.is_favorite]

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

    # ------------------------------------------------------------------
    # Feature: prompt filter
    # ------------------------------------------------------------------
    def _apply_filter(self, _text: str = "") -> None:
        """Show/hide cards based on prompt text match + starred filter."""
        self._apply_visibility()
