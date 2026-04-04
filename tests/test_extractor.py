"""Tests for core/extractor.py"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.extractor import extract_frames, get_video_duration
from core.models import ExtractionError


# ---------------------------------------------------------------------------
# get_video_duration
# ---------------------------------------------------------------------------
@patch("core.extractor.subprocess.run")
@patch("core.extractor._require_binary", return_value="ffprobe")
def test_get_video_duration_success(mock_req, mock_run, tmp_path):
    video = tmp_path / "test.mp4"
    video.write_bytes(b"x")

    payload = {"streams": [{"duration": "123.456"}]}
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(payload), stderr="")

    assert get_video_duration(video) == pytest.approx(123.456)


@patch("core.extractor.subprocess.run")
@patch("core.extractor._require_binary", return_value="ffprobe")
def test_get_video_duration_ffprobe_error(mock_req, mock_run, tmp_path):
    video = tmp_path / "test.mp4"
    video.write_bytes(b"x")
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error!")

    with pytest.raises(ExtractionError, match="ffprobe error"):
        get_video_duration(video)


# ---------------------------------------------------------------------------
# extract_frames
# ---------------------------------------------------------------------------
@patch("core.extractor.subprocess.run")
@patch("core.extractor._require_binary", return_value="ffmpeg")
def test_extract_frames_success(mock_req, mock_run, tmp_path):
    video = tmp_path / "test.mp4"
    video.write_bytes(b"x")
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    # Simulate ffmpeg creating frame files
    def _fake_run(cmd, **kwargs):
        for i in range(1, 4):
            (frames_dir / f"frame_{i:04d}.jpg").write_bytes(b"jpg")
        return MagicMock(returncode=0, stdout="", stderr="")

    mock_run.side_effect = _fake_run

    frames = extract_frames(video, interval_sec=5, output_dir=frames_dir)
    assert len(frames) == 3
    assert frames[0].name == "frame_0001.jpg"


@patch("core.extractor.subprocess.run")
@patch("core.extractor._require_binary", return_value="ffmpeg")
def test_extract_frames_no_output_raises(mock_req, mock_run, tmp_path):
    video = tmp_path / "test.mp4"
    video.write_bytes(b"x")
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    with pytest.raises(ExtractionError, match="no frames"):
        extract_frames(video, interval_sec=1, output_dir=frames_dir)


@patch("core.extractor.subprocess.run")
@patch("core.extractor._require_binary", return_value="ffmpeg")
def test_extract_frames_ffmpeg_error(mock_req, mock_run, tmp_path):
    video = tmp_path / "test.mp4"
    video.write_bytes(b"x")
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Invalid data")

    with pytest.raises(ExtractionError, match="ffmpeg error"):
        extract_frames(video, interval_sec=5, output_dir=frames_dir)


def test_extract_frames_interval_zero_raises(tmp_path):
    with pytest.raises(ExtractionError, match="interval_sec must be"):
        extract_frames(tmp_path / "x.mp4", interval_sec=0, output_dir=tmp_path)


@patch("core.extractor._require_binary")
def test_ffmpeg_not_found(mock_req):
    mock_req.side_effect = ExtractionError("ffmpeg not found on PATH")
    with pytest.raises(ExtractionError, match="ffmpeg not found"):
        extract_frames(Path("x.mp4"), interval_sec=1, output_dir=Path("."))
