"""Tests for core/pipeline.py"""
from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch


from core.models import FrameResult, JobConfig


def _make_config(tmp_path: Path) -> JobConfig:
    return JobConfig(
        url="https://youtube.com/watch?v=test",
        interval_sec=5,
        api_key="sk-test",
        output_dir=tmp_path / "output",
        prompt_type="image",
        max_frames=0,
    )


def _make_frames(frames_dir: Path, n: int) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(1, n + 1):
        p = frames_dir / f"frame_{i:04d}.jpg"
        p.write_bytes(b"\xff\xd8\xff" + b"\x00" * 5)
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Pipeline.run — happy path
# ---------------------------------------------------------------------------
@patch("core.pipeline._get_video_metadata", return_value={})
@patch("core.pipeline.write_summary_md")
@patch("core.pipeline.write_results_json")
@patch("core.pipeline.create_output_dir")
@patch("core.pipeline.analyze_frame", return_value="beautiful sunset prompt")
@patch("core.pipeline.extract_frames")
@patch("core.pipeline.download_video")
def test_pipeline_run_success(
    mock_dl, mock_extract, mock_analyze, mock_create_dir, mock_json, mock_md, mock_meta, tmp_path
):
    config = _make_config(tmp_path)
    out_dir = tmp_path / "output" / "vid_20260101_120000"
    out_dir.mkdir(parents=True)
    frames_dir = out_dir / "frames"
    mock_create_dir.return_value = out_dir

    video_file = out_dir / "testvid.mp4"
    video_file.write_bytes(b"fake-video")
    mock_dl.return_value = video_file

    frames = _make_frames(frames_dir, 3)
    mock_extract.return_value = frames

    progress_calls: list[tuple] = []
    frame_calls: list[FrameResult] = []

    from core.pipeline import Pipeline
    result = Pipeline().run(
        config,
        on_progress=lambda c, t, m: progress_calls.append((c, t, m)),
        on_frame_done=lambda f: frame_calls.append(f),
        stop_event=threading.Event(),
    )

    assert result.success
    assert len(result.frames) == 3
    assert all(f.prompt == "beautiful sunset prompt" for f in result.frames)
    assert len(frame_calls) == 3


@patch("core.pipeline._get_video_metadata", return_value={})
@patch("core.pipeline.write_summary_md")
@patch("core.pipeline.write_results_json")
@patch("core.pipeline.create_output_dir")
@patch("core.pipeline.analyze_frame", return_value="prompt")
@patch("core.pipeline.extract_frames")
@patch("core.pipeline.download_video")
def test_pipeline_stop_event_cancels(
    mock_dl, mock_extract, mock_analyze, mock_create_dir, mock_json, mock_md, mock_meta, tmp_path
):
    config = _make_config(tmp_path)
    out_dir = tmp_path / "output" / "vid_x"
    out_dir.mkdir(parents=True)
    frames_dir = out_dir / "frames"
    mock_create_dir.return_value = out_dir

    video_file = out_dir / "vid.mp4"
    video_file.write_bytes(b"x")
    mock_dl.return_value = video_file

    frames = _make_frames(frames_dir, 5)
    mock_extract.return_value = frames

    stop = threading.Event()
    stop.set()  # cancel immediately before vision loop

    from core.pipeline import Pipeline
    result = Pipeline().run(
        config,
        on_progress=lambda *a: None,
        on_frame_done=lambda f: None,
        stop_event=stop,
    )

    assert "cancel" in result.error_message.lower()
    assert len(result.frames) == 0


@patch("core.pipeline._get_video_metadata", return_value={})
@patch("core.pipeline.create_output_dir")
@patch("core.pipeline.download_video", side_effect=Exception("Network timeout"))
def test_pipeline_download_error_captured(mock_dl, mock_create_dir, mock_meta, tmp_path):
    config = _make_config(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    mock_create_dir.return_value = out_dir

    from core.pipeline import Pipeline
    result = Pipeline().run(
        config,
        on_progress=lambda *a: None,
        on_frame_done=lambda f: None,
        stop_event=threading.Event(),
    )
    assert not result.success
    assert "Network timeout" in result.error_message


@patch("core.pipeline._get_video_metadata", return_value={})
@patch("core.pipeline.write_summary_md")
@patch("core.pipeline.write_results_json")
@patch("core.pipeline.create_output_dir")
@patch("core.pipeline.analyze_frame")
@patch("core.pipeline.extract_frames")
@patch("core.pipeline.download_video")
def test_pipeline_max_frames_limit(
    mock_dl, mock_extract, mock_analyze, mock_create_dir, mock_json, mock_md, mock_meta, tmp_path
):
    config = JobConfig(
        url="https://youtube.com/watch?v=test",
        interval_sec=5,
        api_key="sk-test",
        output_dir=tmp_path,
        prompt_type="image",
        max_frames=2,
    )

    out_dir = tmp_path / "vid_20260101_120000"
    out_dir.mkdir(parents=True)
    frames_dir = out_dir / "frames"
    mock_create_dir.return_value = out_dir
    video_file = out_dir / "vid.mp4"
    video_file.write_bytes(b"x")
    mock_dl.return_value = video_file
    frames = _make_frames(frames_dir, 10)
    mock_extract.return_value = frames
    mock_analyze.return_value = "a prompt"

    from core.pipeline import Pipeline
    result = Pipeline().run(
        config,
        on_progress=lambda *a: None,
        on_frame_done=lambda f: None,
        stop_event=threading.Event(),
    )
    assert len(result.frames) == 2
