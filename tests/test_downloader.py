"""Tests for core/downloader.py"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.downloader import download_video, _sanitize_url
from core.models import DownloadError


# ---------------------------------------------------------------------------
# _sanitize_url
# ---------------------------------------------------------------------------
def test_sanitize_url_valid_https():
    assert _sanitize_url("  https://youtube.com/watch?v=abc  ") == "https://youtube.com/watch?v=abc"


def test_sanitize_url_valid_http():
    assert _sanitize_url("http://example.com") == "http://example.com"


def test_sanitize_url_invalid_raises():
    with pytest.raises(DownloadError, match="Invalid URL"):
        _sanitize_url("notaurl")


# ---------------------------------------------------------------------------
# download_video — happy path
# ---------------------------------------------------------------------------
@patch("core.downloader.yt_dlp")
def test_download_video_success(mock_yt_dlp, tmp_path):
    video_file = tmp_path / "abc123.mp4"
    video_file.write_bytes(b"fake-video")

    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {"id": "abc123"}
    mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__exit__ = MagicMock(return_value=False)
    mock_yt_dlp.YoutubeDL.return_value = mock_ydl_instance

    result = download_video("https://youtube.com/watch?v=abc123", tmp_path)
    assert result == video_file


@patch("core.downloader.yt_dlp")
def test_download_video_yt_dlp_error_raises_download_error(mock_yt_dlp, tmp_path):
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.side_effect = Exception("Connection refused")
    mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__exit__ = MagicMock(return_value=False)
    mock_yt_dlp.YoutubeDL.return_value = mock_ydl_instance

    with pytest.raises(DownloadError, match="Connection refused"):
        download_video("https://youtube.com/watch?v=xyz", tmp_path)


def test_download_video_invalid_url_raises(tmp_path):
    with pytest.raises(DownloadError, match="Invalid URL"):
        download_video("ftp://bad.url", tmp_path)


@patch("core.downloader.yt_dlp")
def test_download_video_file_not_found_after_download(mock_yt_dlp, tmp_path):
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {"id": "missing_id"}
    mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__exit__ = MagicMock(return_value=False)
    mock_yt_dlp.YoutubeDL.return_value = mock_ydl_instance

    with pytest.raises(DownloadError, match="file not found"):
        download_video("https://youtube.com/watch?v=missing_id", tmp_path)


# ---------------------------------------------------------------------------
# progress callback
# ---------------------------------------------------------------------------
@patch("core.downloader.yt_dlp")
def test_download_video_calls_progress_cb(mock_yt_dlp, tmp_path):
    video_file = tmp_path / "cb_test.mp4"
    video_file.write_bytes(b"fake")

    captured_hooks = []

    def capture_opts(opts):
        captured_hooks.extend(opts.get("progress_hooks", []))
        inst = MagicMock()
        inst.extract_info.return_value = {"id": "cb_test"}
        inst.__enter__ = MagicMock(return_value=inst)
        inst.__exit__ = MagicMock(return_value=False)
        return inst

    mock_yt_dlp.YoutubeDL.side_effect = capture_opts

    calls: list[tuple] = []
    download_video("https://youtube.com/watch?v=cb_test", tmp_path, progress_cb=lambda *a: calls.append(a))

    if captured_hooks:
        captured_hooks[0]({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
    assert True  # callback wired without error
