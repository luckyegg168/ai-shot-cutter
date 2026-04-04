"""Smoke test: verify app window launches without crashing."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_main_window_launches(qapp, tmp_path):
    """MainWindow should open without error."""
    from utils.settings import AppSettings
    from ui.main_window import MainWindow

    settings = AppSettings()
    window = MainWindow(settings)
    window.show()
    assert window.isVisible()
    window.close()


def test_input_panel_validation(qapp, tmp_path):
    """Start button should be disabled until valid URL + API key provided."""
    from utils.settings import AppSettings
    from ui.input_panel import InputPanel

    settings = AppSettings()
    panel = InputPanel(settings)
    panel.show()

    # Empty URL → disabled
    panel._url_edit.setText("")
    panel._api_edit.setText("sk-valid")
    panel._validate()
    assert not panel._btn_start.isEnabled()

    # Valid URL + key → enabled
    panel._url_edit.setText("https://youtube.com/watch?v=dQw4w9WgXcQ")
    panel._api_edit.setText("sk-valid-key")
    panel._validate()
    assert panel._btn_start.isEnabled()

    panel.close()


def test_gallery_add_and_clear(qapp, tmp_path):
    """GalleryWidget should add cards and clear them."""
    from ui.gallery_widget import GalleryWidget
    from core.models import FrameResult

    # Create a fake JPEG
    img = tmp_path / "frame_0001.jpg"
    img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)

    gallery = GalleryWidget()
    gallery.show()

    fr = FrameResult(index=1, timestamp_sec=0.0, image_path=img, prompt="test prompt")
    gallery.add_frame_card(fr)
    assert len(gallery._cards) == 1

    gallery.clear()
    assert len(gallery._cards) == 0

    gallery.close()


def test_log_panel_appends(qapp):
    """LogPanel should accept info/warning/error messages."""
    from ui.log_panel import LogPanel

    panel = LogPanel()
    panel.show()
    panel.log_info("Info message")
    panel.log_warning("Warning message")
    panel.log_error("Error message")
    text = panel._log_edit.toPlainText()
    assert "Info message" in text
    assert "Warning message" in text
    assert "Error message" in text
    panel.close()
