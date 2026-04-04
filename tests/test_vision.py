"""Tests for core/vision.py"""
from __future__ import annotations

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


# ---------------------------------------------------------------------------
# analyze_frame — happy paths
# ---------------------------------------------------------------------------
@patch("core.vision.OpenAI")
def test_analyze_frame_image_prompt(mock_openai_cls, tmp_path):
    img = _make_image(tmp_path)

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="wide cinematic shot, golden hour"))]
    )

    from core.vision import analyze_frame
    result = analyze_frame(img, "sk-test", "image")
    assert "cinematic" in result.lower()


@patch("core.vision.OpenAI")
def test_analyze_frame_video_prompt(mock_openai_cls, tmp_path):
    img = _make_image(tmp_path)

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="slow tracking shot across river"))]
    )

    from core.vision import analyze_frame
    result = analyze_frame(img, "sk-test", "video")
    assert "tracking" in result.lower()


# ---------------------------------------------------------------------------
# analyze_frame — error handling
# ---------------------------------------------------------------------------
@patch("core.vision.OpenAI")
def test_analyze_frame_401_raises_vision_error(mock_openai_cls, tmp_path):
    img = _make_image(tmp_path)

    from openai import APIStatusError  # may not be installed; skip if missing
    pytest.importorskip("openai")

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    err = APIStatusError("Unauthorized", response=MagicMock(status_code=401), body={})
    mock_client.chat.completions.create.side_effect = err

    from core.vision import analyze_frame
    with pytest.raises(VisionError, match="401|Invalid"):
        analyze_frame(img, "sk-bad", "image")


@patch("core.vision.OpenAI")
def test_analyze_frame_empty_response_raises(mock_openai_cls, tmp_path):
    img = _make_image(tmp_path)

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=""))]
    )

    from core.vision import analyze_frame
    with pytest.raises(VisionError, match="empty"):
        analyze_frame(img, "sk-test", "image")


@patch("core.vision.OpenAI")
@patch("core.vision.time.sleep")
def test_analyze_frame_retries_on_500(mock_sleep, mock_openai_cls, tmp_path):
    img = _make_image(tmp_path)
    pytest.importorskip("openai")
    from openai import APIStatusError

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    # Fail 3 times then succeed
    err = APIStatusError("Server error", response=MagicMock(status_code=503), body={})
    mock_client.chat.completions.create.side_effect = [
        err, err, err,
        MagicMock(choices=[MagicMock(message=MagicMock(content="recovered"))]),
    ]

    from core.vision import analyze_frame
    result = analyze_frame(img, "sk-test", "image")
    assert result == "recovered"
    assert mock_sleep.call_count >= 2
