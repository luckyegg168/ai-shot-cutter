"""Video editing tools — pure Python, no Qt imports.

Ten practical features for video editing workflow:
1. Scene change detection (ffmpeg scene filter)
2. Video trimming (start/end time)
3. Frame comparison (side-by-side image)
4. GIF preview export (from selected frames)
5. Audio extraction (mp3/wav)
6. Watermark overlay (text or image)
7. Auto best-frame selection (sharpness scoring)
8. SRT subtitle export (from prompt results)
9. Batch prompt template rendering
10. Project save/load (JSON session)
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .models import ExtractionError, FrameResult


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise ExtractionError("ffmpeg not found on PATH")
    return path


# ─────────────────────────────────────────────────────────────────────
# 1. Scene change detection
# ─────────────────────────────────────────────────────────────────────
def detect_scene_changes(
    video_path: Path,
    threshold: float = 0.3,
    output_dir: Path | None = None,
) -> list[float]:
    """Detect scene changes and return timestamps (seconds).

    Uses ffmpeg's scene detection filter. Higher threshold = fewer scenes.

    Args:
        video_path: Path to video file.
        threshold: Scene change sensitivity (0.0–1.0, default 0.3).
        output_dir: If provided, extract a frame at each scene change.

    Returns:
        List of timestamp floats where scene changes occur.
    """
    ffmpeg = _require_ffmpeg()
    cmd = [
        ffmpeg, "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    # Parse showinfo output for pts_time
    timestamps: list[float] = []
    for line in result.stderr.splitlines():
        if "pts_time:" in line:
            for part in line.split():
                if part.startswith("pts_time:"):
                    try:
                        ts = float(part.split(":")[1])
                        timestamps.append(ts)
                    except (ValueError, IndexError):
                        pass

    if output_dir and timestamps:
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, ts in enumerate(timestamps):
            out_path = output_dir / f"scene_{i:04d}.jpg"
            extract_cmd = [
                ffmpeg, "-ss", str(ts),
                "-i", str(video_path),
                "-frames:v", "1", "-q:v", "2",
                str(out_path),
            ]
            subprocess.run(extract_cmd, capture_output=True, timeout=30)

    return timestamps


# ─────────────────────────────────────────────────────────────────────
# 2. Video trimming
# ─────────────────────────────────────────────────────────────────────
def trim_video(
    video_path: Path,
    start_sec: float,
    end_sec: float,
    output_path: Path,
) -> Path:
    """Trim video from start_sec to end_sec.

    Args:
        video_path: Source video.
        start_sec: Start time in seconds.
        end_sec: End time in seconds.
        output_path: Output file path.

    Returns:
        Path to the trimmed video.
    """
    if end_sec <= start_sec:
        raise ExtractionError("end_sec must be greater than start_sec")
    ffmpeg = _require_ffmpeg()
    duration = end_sec - start_sec
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-ss", str(start_sec),
        "-i", str(video_path),
        "-t", str(duration),
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise ExtractionError(f"Trim failed: {proc.stderr[:300]}")
    if not output_path.exists():
        raise ExtractionError(f"Trim output not found: {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 3. Frame comparison (side-by-side)
# ─────────────────────────────────────────────────────────────────────
def compare_frames(
    frame_a: Path,
    frame_b: Path,
    output_path: Path,
) -> Path:
    """Create a side-by-side comparison image using ffmpeg.

    Returns:
        Path to the comparison image.
    """
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-i", str(frame_a),
        "-i", str(frame_b),
        "-filter_complex", "hstack=inputs=2",
        "-q:v", "2",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise ExtractionError(f"Compare failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 4. GIF preview export
# ─────────────────────────────────────────────────────────────────────
def export_gif(
    frame_paths: Sequence[Path],
    output_path: Path,
    fps: int = 2,
    width: int = 480,
) -> Path:
    """Create an animated GIF from a sequence of frames.

    Args:
        frame_paths: Ordered list of JPEG frame paths.
        output_path: Output .gif path.
        fps: Frames per second in the GIF.
        width: Width in pixels (height auto-scaled).

    Returns:
        Path to the generated GIF.
    """
    if not frame_paths:
        raise ExtractionError("No frames provided for GIF export")
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build concat file
    concat_file = output_path.parent / "_gif_concat.txt"
    lines = [f"file '{p}'\nduration {1/fps}" for p in frame_paths]
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", f"scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    concat_file.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise ExtractionError(f"GIF export failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 5. Audio extraction
# ─────────────────────────────────────────────────────────────────────
def extract_audio(
    video_path: Path,
    output_path: Path,
    format: str = "mp3",
) -> Path:
    """Extract audio track from video.

    Args:
        video_path: Source video.
        output_path: Output audio file path.
        format: "mp3" or "wav".

    Returns:
        Path to extracted audio.
    """
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if format == "wav":
        codec_args = ["-acodec", "pcm_s16le", "-ar", "44100"]
    else:
        codec_args = ["-acodec", "libmp3lame", "-ab", "192k"]
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vn",
        *codec_args,
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise ExtractionError(f"Audio extraction failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 6. Watermark overlay (text)
# ─────────────────────────────────────────────────────────────────────
def add_text_watermark(
    video_path: Path,
    output_path: Path,
    text: str,
    position: str = "bottom_right",
    font_size: int = 24,
) -> Path:
    """Add text watermark to video.

    Args:
        video_path: Source video.
        output_path: Output video path.
        text: Watermark text.
        position: One of "top_left", "top_right", "bottom_left", "bottom_right", "center".
        font_size: Font size in pixels.

    Returns:
        Path to watermarked video.
    """
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Escape special characters for ffmpeg drawtext
    safe_text = text.replace("'", "\\'").replace(":", "\\:")
    pos_map = {
        "top_left": "x=10:y=10",
        "top_right": "x=w-tw-10:y=10",
        "bottom_left": "x=10:y=h-th-10",
        "bottom_right": "x=w-tw-10:y=h-th-10",
        "center": "x=(w-tw)/2:y=(h-th)/2",
    }
    pos = pos_map.get(position, pos_map["bottom_right"])
    vf = f"drawtext=text='{safe_text}':fontsize={font_size}:fontcolor=white@0.7:{pos}"
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-codec:a", "copy",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise ExtractionError(f"Watermark failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 7. Auto best-frame selection (sharpness ranking)
# ─────────────────────────────────────────────────────────────────────
def rank_frames_by_sharpness(frame_paths: Sequence[Path], top_n: int = 5) -> list[tuple[Path, float]]:
    """Rank frames by sharpness (Laplacian variance).

    Returns:
        List of (path, score) sorted by score descending. Higher = sharper.
    """
    scores: list[tuple[Path, float]] = []
    for fp in frame_paths:
        try:
            import cv2
            img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                score = float(cv2.Laplacian(img, cv2.CV_64F).var())
                scores.append((fp, score))
            else:
                scores.append((fp, 0.0))
        except ImportError:
            # cv2 not available — use file size as rough proxy
            scores.append((fp, float(fp.stat().st_size)))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_n]


# ─────────────────────────────────────────────────────────────────────
# 8. SRT subtitle export
# ─────────────────────────────────────────────────────────────────────
def export_srt(
    frames: Sequence[FrameResult],
    output_path: Path,
    duration_per_frame: float = 5.0,
) -> Path:
    """Export frame prompts as SRT subtitle file.

    Each frame prompt becomes a subtitle entry.

    Args:
        frames: Sequence of FrameResult.
        output_path: Output .srt path.
        duration_per_frame: How long each subtitle shows (seconds).

    Returns:
        Path to the SRT file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i, fr in enumerate(frames, 1):
        start = fr.timestamp_sec
        end = start + duration_per_frame
        lines.append(str(i))
        lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
        lines.append(fr.prompt.strip())
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ─────────────────────────────────────────────────────────────────────
# 9. Batch prompt template rendering
# ─────────────────────────────────────────────────────────────────────
def render_prompt_template(
    template: str,
    frames: Sequence[FrameResult],
) -> str:
    """Render a user-defined template using frame data.

    Supported placeholders: {index}, {timestamp}, {prompt}

    Args:
        template: Template string with placeholders.
        frames: Sequence of FrameResult.

    Returns:
        Rendered text.
    """
    parts: list[str] = []
    for fr in frames:
        rendered = template.replace("{index}", str(fr.index))
        rendered = rendered.replace("{timestamp}", fr.timestamp_label)
        rendered = rendered.replace("{prompt}", fr.prompt)
        rendered = rendered.replace("{image_path}", str(fr.image_path))
        parts.append(rendered)
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# 10. Project save/load (JSON session)
# ─────────────────────────────────────────────────────────────────────
def save_project(
    filepath: Path,
    config_dict: dict,
    frames: Sequence[FrameResult],
) -> Path:
    """Save project state to JSON.

    Args:
        filepath: Output .json path.
        config_dict: Serializable dict of JobConfig fields.
        frames: All FrameResult objects.

    Returns:
        Path to the saved project file.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": "1.0",
        "config": config_dict,
        "frames": [
            {
                "index": fr.index,
                "timestamp_sec": fr.timestamp_sec,
                "image_path": str(fr.image_path),
                "prompt": fr.prompt,
            }
            for fr in frames
        ],
    }
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return filepath


def load_project(filepath: Path) -> tuple[dict, list[FrameResult]]:
    """Load project state from JSON.

    Returns:
        (config_dict, list of FrameResult)
    """
    data = json.loads(filepath.read_text(encoding="utf-8"))
    config_dict = data.get("config", {})
    frames: list[FrameResult] = []
    for fd in data.get("frames", []):
        frames.append(FrameResult(
            index=fd["index"],
            timestamp_sec=fd["timestamp_sec"],
            image_path=Path(fd["image_path"]),
            prompt=fd["prompt"],
        ))
    return config_dict, frames
