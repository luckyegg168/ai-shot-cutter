"""Tests for core/tools.py — video editing tools (no ffmpeg/cv2 required)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.models import ExtractionError, FrameResult
from core.tools import (
    _fmt_srt_time,
    _require_ffmpeg,
    add_text_watermark,
    compare_frames,
    detect_scene_changes,
    export_gif,
    export_srt,
    extract_audio,
    load_project,
    rank_frames_by_sharpness,
    render_prompt_template,
    save_project,
    trim_video,
)


# ── Helpers ──────────────────────────────────────────────────────────
def _make_frame(tmp_path: Path, index: int, timestamp: float = 0.0, prompt: str = "test") -> FrameResult:
    """Create a minimal FrameResult with a dummy image file."""
    fp = tmp_path / f"frame_{index:04d}.jpg"
    fp.write_bytes(b"\xff\xd8dummy")
    return FrameResult(index=index, timestamp_sec=timestamp, image_path=fp, prompt=prompt)


# ── _require_ffmpeg ──────────────────────────────────────────────────
class TestRequireFfmpeg:
    def test_found(self):
        with patch("core.tools.shutil.which", return_value="/usr/bin/ffmpeg"):
            assert _require_ffmpeg() == "/usr/bin/ffmpeg"

    def test_not_found(self):
        with patch("core.tools.shutil.which", return_value=None):
            with pytest.raises(ExtractionError, match="ffmpeg not found"):
                _require_ffmpeg()


# ── 1. detect_scene_changes ──────────────────────────────────────────
class TestDetectSceneChanges:
    def test_parses_timestamps(self, tmp_path: Path):
        stderr = (
            "[Parsed_showinfo_1 @ 0x1] n:0 pts:12345 pts_time:1.500 fmt:yuv420p\n"
            "[Parsed_showinfo_1 @ 0x1] n:1 pts:67890 pts_time:5.250 fmt:yuv420p\n"
        )
        mock_result = MagicMock(returncode=0, stderr=stderr)
        with patch("core.tools.subprocess.run", return_value=mock_result), \
             patch("core.tools._require_ffmpeg", return_value="ffmpeg"):
            ts = detect_scene_changes(tmp_path / "video.mp4", threshold=0.3)
        assert ts == [1.5, 5.25]

    def test_empty_on_no_scenes(self, tmp_path: Path):
        mock_result = MagicMock(returncode=0, stderr="")
        with patch("core.tools.subprocess.run", return_value=mock_result), \
             patch("core.tools._require_ffmpeg", return_value="ffmpeg"):
            ts = detect_scene_changes(tmp_path / "video.mp4")
        assert ts == []


# ── 2. trim_video ────────────────────────────────────────────────────
class TestTrimVideo:
    def test_success(self, tmp_path: Path):
        out = tmp_path / "trimmed.mp4"
        # Create output file to simulate ffmpeg output
        mock_result = MagicMock(returncode=0)
        def side_effect(*a, **kw):
            out.write_bytes(b"video")
            return mock_result
        with patch("core.tools.subprocess.run", side_effect=side_effect), \
             patch("core.tools._require_ffmpeg", return_value="ffmpeg"):
            result = trim_video(tmp_path / "video.mp4", 5.0, 15.0, out)
        assert result == out

    def test_invalid_range(self, tmp_path: Path):
        with pytest.raises(ExtractionError, match="end_sec must be greater"):
            trim_video(tmp_path / "v.mp4", 10.0, 5.0, tmp_path / "out.mp4")


# ── 3. compare_frames ────────────────────────────────────────────────
class TestCompareFrames:
    def test_success(self, tmp_path: Path):
        a = tmp_path / "a.jpg"
        b = tmp_path / "b.jpg"
        a.write_bytes(b"img")
        b.write_bytes(b"img")
        out = tmp_path / "cmp.jpg"
        mock_result = MagicMock(returncode=0)
        with patch("core.tools.subprocess.run", return_value=mock_result), \
             patch("core.tools._require_ffmpeg", return_value="ffmpeg"):
            compare_frames(a, b, out)


# ── 4. export_gif ────────────────────────────────────────────────────
class TestExportGif:
    def test_no_frames(self):
        with pytest.raises(ExtractionError, match="No frames"):
            export_gif([], Path("out.gif"))

    def test_creates_concat_file(self, tmp_path: Path):
        f1 = tmp_path / "f1.jpg"
        f2 = tmp_path / "f2.jpg"
        f1.write_bytes(b"a")
        f2.write_bytes(b"b")
        out = tmp_path / "out.gif"

        mock_result = MagicMock(returncode=0)
        with patch("core.tools.subprocess.run", return_value=mock_result), \
             patch("core.tools._require_ffmpeg", return_value="ffmpeg"):
            export_gif([f1, f2], out, fps=2, width=320)
        # concat file should be cleaned up
        assert not (tmp_path / "_gif_concat.txt").exists()


# ── 5. extract_audio ─────────────────────────────────────────────────
class TestExtractAudio:
    @pytest.mark.parametrize("fmt", ["mp3", "wav"])
    def test_formats(self, tmp_path: Path, fmt: str):
        out = tmp_path / f"audio.{fmt}"
        mock_result = MagicMock(returncode=0)
        with patch("core.tools.subprocess.run", return_value=mock_result), \
             patch("core.tools._require_ffmpeg", return_value="ffmpeg"):
            extract_audio(tmp_path / "video.mp4", out, format=fmt)


# ── 6. add_text_watermark ────────────────────────────────────────────
class TestAddTextWatermark:
    @pytest.mark.parametrize("pos", ["top_left", "top_right", "bottom_left", "bottom_right", "center"])
    def test_positions(self, tmp_path: Path, pos: str):
        out = tmp_path / "wm.mp4"
        mock_result = MagicMock(returncode=0)
        with patch("core.tools.subprocess.run", return_value=mock_result), \
             patch("core.tools._require_ffmpeg", return_value="ffmpeg"):
            add_text_watermark(tmp_path / "v.mp4", out, "Test", position=pos)


# ── 7. rank_frames_by_sharpness ──────────────────────────────────────
class TestRankFramesBySharpness:
    def test_returns_top_n(self, tmp_path: Path):
        frames = []
        for i in range(5):
            fp = tmp_path / f"f_{i}.jpg"
            fp.write_bytes(b"x" * ((i + 1) * 100))
            frames.append(fp)
        # Without cv2, falls back to file size
        with patch.dict("sys.modules", {"cv2": None}):
            ranked = rank_frames_by_sharpness(frames, top_n=3)
        assert len(ranked) == 3
        # Each entry is (Path, float)
        for path, score in ranked:
            assert isinstance(path, Path)
            assert isinstance(score, float)


# ── 8. export_srt ────────────────────────────────────────────────────
class TestExportSrt:
    def test_basic(self, tmp_path: Path):
        frames = [
            _make_frame(tmp_path, 1, 0.0, "Scene one"),
            _make_frame(tmp_path, 2, 10.0, "Scene two"),
        ]
        out = tmp_path / "subs.srt"
        result = export_srt(frames, out, duration_per_frame=5.0)
        assert result == out
        content = out.read_text(encoding="utf-8")
        assert "Scene one" in content
        assert "Scene two" in content
        assert "00:00:00,000 --> 00:00:05,000" in content
        assert "00:00:10,000 --> 00:00:15,000" in content


class TestFmtSrtTime:
    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0.0, "00:00:00,000"),
            (61.5, "00:01:01,500"),
            (3661.123, "01:01:01,123"),
        ],
    )
    def test_format(self, seconds, expected):
        assert _fmt_srt_time(seconds) == expected


# ── 9. render_prompt_template ────────────────────────────────────────
class TestRenderPromptTemplate:
    def test_basic(self, tmp_path: Path):
        frames = [
            _make_frame(tmp_path, 1, 5.0, "Hello"),
            _make_frame(tmp_path, 2, 10.0, "World"),
        ]
        tpl = "{index}. [{timestamp}] {prompt}"
        result = render_prompt_template(tpl, frames)
        assert "1. [0:05] Hello" in result
        assert "2. [0:10] World" in result

    def test_image_path_placeholder(self, tmp_path: Path):
        fr = _make_frame(tmp_path, 1, 0.0, "prompt")
        tpl = "File: {image_path}"
        result = render_prompt_template(tpl, [fr])
        assert str(fr.image_path) in result


# ── 10. save/load project ───────────────────────────────────────────
class TestProjectSaveLoad:
    def test_roundtrip(self, tmp_path: Path):
        frames = [
            _make_frame(tmp_path, 1, 0.0, "First frame"),
            _make_frame(tmp_path, 2, 5.0, "Second frame"),
        ]
        config = {"url": "https://example.com", "interval_sec": 5}
        proj_file = tmp_path / "project.json"
        save_project(proj_file, config, frames)
        assert proj_file.exists()

        loaded_config, loaded_frames = load_project(proj_file)
        assert loaded_config["url"] == "https://example.com"
        assert len(loaded_frames) == 2
        assert loaded_frames[0].prompt == "First frame"
        assert loaded_frames[1].timestamp_sec == 5.0

    def test_json_structure(self, tmp_path: Path):
        frames = [_make_frame(tmp_path, 1, 0.0, "test")]
        proj_file = tmp_path / "project.json"
        save_project(proj_file, {}, frames)
        data = json.loads(proj_file.read_text(encoding="utf-8"))
        assert data["version"] == "1.0"
        assert "config" in data
        assert "frames" in data
        assert len(data["frames"]) == 1
