"""ffmpeg wrapper — pure Python, no Qt imports."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .models import ExtractionError


def _require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ExtractionError(
            f"'{name}' not found on PATH. "
            "Install it with: winget install ffmpeg   (Windows) "
            "or: brew install ffmpeg   (macOS)"
        )
    return path


def get_video_duration(video_path: Path) -> float:
    """Return video duration in seconds using ffprobe.

    Raises:
        ExtractionError: If ffprobe fails or duration cannot be parsed.
    """
    ffprobe = _require_binary("ffprobe")
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(video_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError("ffprobe timed out") from exc

    if result.returncode != 0:
        raise ExtractionError(f"ffprobe error: {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            duration = stream.get("duration")
            if duration:
                return float(duration)
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        raise ExtractionError(f"Cannot parse ffprobe output: {exc}") from exc

    raise ExtractionError("Could not determine video duration from ffprobe output")


def extract_frames(
    video_path: Path,
    interval_sec: int,
    output_dir: Path,
) -> list[Path]:
    """Extract one frame every interval_sec seconds using ffmpeg.

    Args:
        video_path: Path to the source video file.
        interval_sec: Seconds between frames (1–300).
        output_dir: Directory to write frame JPEGs.

    Returns:
        Sorted list of extracted frame paths.

    Raises:
        ExtractionError: On ffmpeg failure or no frames extracted.
    """
    if interval_sec < 1:
        raise ExtractionError("interval_sec must be >= 1")

    ffmpeg = _require_binary("ffmpeg")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_pattern = str(output_dir / "frame_%04d.jpg")

    cmd = [
        ffmpeg,
        "-i", str(video_path),
        "-vf", f"fps=1/{interval_sec}",
        "-q:v", "2",
        "-y",           # overwrite without prompt
        output_pattern,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError("ffmpeg timed out after 10 minutes") from exc

    if result.returncode != 0:
        raise ExtractionError(f"ffmpeg error:\n{result.stderr.strip()}")

    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        raise ExtractionError(
            "ffmpeg produced no frames. The video may be too short "
            f"for interval_sec={interval_sec}."
        )

    return frames
