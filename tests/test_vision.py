"""Tests for core/vision.py"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.models import VisionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_image(tmp_path: Path) -> Path:
    """Create a minimal fake JPEG."""
    p = tmp_path / "frame_0001.jpg"
    p.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)
    return p


class _FakeAPIStatusError(Exception):
    """Lightweight stand-in for openai.APIStatusError."""
    def __init__(self, message: str, *, status_code: int):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _install_fake_openai() -> MagicMock:
    """Insert a fake 'openai' package into sys.modules and return the mock."""
    fake = MagicMock()
    fake.APIStatusError = _FakeAPIStatusError
    sys.modules["openai"] = fake
    return fake


def _cleanup_fake_openai():
    sys.modules.pop("openai", None)


# ---------------------------------------------------------------------------
# analyze_frame — happy paths
# ---------------------------------------------------------------------------
def test_analyze_frame_image_prompt(tmp_path):
    fake = _install_fake_openai()
    try:
        img = _make_image(tmp_path)

        mock_client = MagicMock()
        fake.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="wide cinematic shot, golden hour"))]
        )

        from core.vision import analyze_frame
        result = analyze_frame(img, "sk-test", "image")
        assert "cinematic" in result.lower()
    finally:
        _cleanup_fake_openai()


def test_analyze_frame_video_prompt(tmp_path):
    fake = _install_fake_openai()
    try:
        img = _make_image(tmp_path)

        mock_client = MagicMock()
        fake.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="slow tracking shot across river"))]
        )

        from core.vision import analyze_frame
        result = analyze_frame(img, "sk-test", "video")
        assert "tracking" in result.lower()
    finally:
        _cleanup_fake_openai()


# ---------------------------------------------------------------------------
# analyze_frame — error handling
# ---------------------------------------------------------------------------
def test_analyze_frame_401_raises_vision_error(tmp_path):
    fake = _install_fake_openai()
    try:
        img = _make_image(tmp_path)

        mock_client = MagicMock()
        fake.OpenAI.return_value = mock_client

        err = _FakeAPIStatusError("Unauthorized", status_code=401)
        mock_client.chat.completions.create.side_effect = err

        from core.vision import analyze_frame
        with pytest.raises(VisionError, match="401|Invalid"):
            analyze_frame(img, "sk-bad", "image")
    finally:
        _cleanup_fake_openai()


def test_analyze_frame_empty_response_raises(tmp_path):
    fake = _install_fake_openai()
    try:
        img = _make_image(tmp_path)

        mock_client = MagicMock()
        fake.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=""))]
        )

        from core.vision import analyze_frame
        with pytest.raises(VisionError, match="empty"):
            analyze_frame(img, "sk-test", "image")
    finally:
        _cleanup_fake_openai()


@patch("core.vision.time.sleep")
def test_analyze_frame_retries_on_500(mock_sleep, tmp_path):
    fake = _install_fake_openai()
    try:
        img = _make_image(tmp_path)

        mock_client = MagicMock()
        fake.OpenAI.return_value = mock_client

        err = _FakeAPIStatusError("Server error", status_code=503)
        mock_client.chat.completions.create.side_effect = [
            err, err, err,
            MagicMock(choices=[MagicMock(message=MagicMock(content="recovered"))]),
        ]

        from core.vision import analyze_frame
        result = analyze_frame(img, "sk-test", "image")
        assert result == "recovered"
        assert mock_sleep.call_count >= 2
    finally:
        _cleanup_fake_openai()
