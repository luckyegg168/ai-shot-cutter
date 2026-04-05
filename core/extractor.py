"""ffmpeg wrapper — pure Python, no Qt imports."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from .models import ExtractionError

logger = logging.getLogger(__name__)

# Hardware accelerators tried in priority order (Windows-first list).
# Each entry: (hwaccel_name, extra_input_flags)
_HWACCEL_CANDIDATES: list[tuple[str, list[str]]] = [
    ("cuda",    ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]),
    ("d3d11va", ["-hwaccel", "d3d11va"]),
    ("dxva2",   ["-hwaccel", "dxva2"]),
]


def _probe_hwaccels(ffmpeg: str) -> list[str]:
    """Return hwaccel names that ffmpeg reports as available."""
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-hwaccels"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.splitlines()
        # Output format: first line is header, rest are hwaccel names
        return [ln.strip() for ln in lines[1:] if ln.strip()]
    except Exception:
        return []


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

    def _build_cmd(extra_input_flags: list[str]) -> list[str]:
        return [
            ffmpeg,
            *extra_input_flags,
            "-i", str(video_path),
            "-vf", f"fps=1/{interval_sec}",
            "-q:v", "2",
            "-y",
            output_pattern,
        ]

    # Build ordered list of commands to try: GPU candidates first, then CPU.
    available_hwaccels = _probe_hwaccels(ffmpeg)
    candidates: list[tuple[str, list[str]]] = []
    for name, flags in _HWACCEL_CANDIDATES:
        if name in available_hwaccels:
            candidates.append((name, flags))
    candidates.append(("cpu", []))   # always append CPU fallback

    last_error = ""
    for decoder_name, extra_flags in candidates:
        cmd = _build_cmd(extra_flags)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExtractionError("ffmpeg timed out after 10 minutes") from exc

        if result.returncode == 0:
            if decoder_name != "cpu":
                logger.info("Frame extraction using hardware decoder: %s", decoder_name)
            else:
                if last_error:
                    logger.warning(
                        "GPU decode failed (%s), fell back to CPU.", last_error[:120]
                    )
                logger.info("Frame extraction using CPU decoder")
            break

        last_error = result.stderr.strip()
        logger.debug(
            "hwaccel '%s' failed (rc=%d), trying next. stderr: %s",
            decoder_name, result.returncode, last_error[:200],
        )
    else:
        raise ExtractionError(f"ffmpeg error:\n{last_error}")

    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        raise ExtractionError(
            "ffmpeg produced no frames. The video may be too short "
            f"for interval_sec={interval_sec}."
        )

    return frames
