"""Video editing tools — pure Python, no Qt imports.

Twenty practical features for video editing workflow:
1.  Scene change detection (ffmpeg scene filter)
2.  Video trimming (start/end time)
3.  Frame comparison (side-by-side image)
4.  GIF preview export (from selected frames)
5.  Audio extraction (mp3/wav)
6.  Watermark overlay (text or image)
7.  Auto best-frame selection (sharpness scoring)
8.  SRT subtitle export (from prompt results)
9.  Batch prompt template rendering
10. Project save/load (JSON session)
11. Video speed change (speed up / slow down)
12. Frame rotate / flip
13. Video thumbnail generator
14. Frame mosaic / contact sheet
15. Video info / stats
16. Frame crop
17. Reverse video
18. Extract all frames (full FPS)
19. Frame deduplication
20. Merge (concatenate) videos
"""
from __future__ import annotations

import json
import shutil
import subprocess
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


# ─────────────────────────────────────────────────────────────────────
# 11. Video speed change
# ─────────────────────────────────────────────────────────────────────
def change_video_speed(
    video_path: Path,
    output_path: Path,
    speed: float = 2.0,
) -> Path:
    """Change video playback speed.

    Args:
        video_path: Source video.
        output_path: Output video path.
        speed: Multiplier (2.0 = 2× faster, 0.5 = half speed).

    Returns:
        Path to the output video.
    """
    if speed <= 0:
        raise ExtractionError("Speed must be > 0")
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pts = 1.0 / speed
    atempo = speed
    # ffmpeg atempo only supports 0.5–2.0; chain if needed
    atempo_filters: list[str] = []
    remaining = atempo
    while remaining > 2.0:
        atempo_filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        atempo_filters.append("atempo=0.5")
        remaining /= 0.5
    atempo_filters.append(f"atempo={remaining:.4f}")
    af = ",".join(atempo_filters)
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vf", f"setpts={pts:.4f}*PTS",
        "-af", af,
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise ExtractionError(f"Speed change failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 12. Frame rotate / flip
# ─────────────────────────────────────────────────────────────────────
def rotate_frame(
    image_path: Path,
    output_path: Path,
    rotation: str = "90cw",
) -> Path:
    """Rotate or flip a frame image.

    Args:
        image_path: Source image.
        output_path: Output image path.
        rotation: One of "90cw", "90ccw", "180", "hflip", "vflip".

    Returns:
        Path to the rotated image.
    """
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf_map = {
        "90cw": "transpose=1",
        "90ccw": "transpose=2",
        "180": "transpose=1,transpose=1",
        "hflip": "hflip",
        "vflip": "vflip",
    }
    vf = vf_map.get(rotation)
    if not vf:
        raise ExtractionError(f"Unknown rotation: {rotation}")
    cmd = [
        ffmpeg, "-y",
        "-i", str(image_path),
        "-vf", vf,
        "-q:v", "2",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise ExtractionError(f"Rotate failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 13. Video thumbnail generator
# ─────────────────────────────────────────────────────────────────────
def generate_thumbnail(
    video_path: Path,
    output_path: Path,
    timestamp_sec: float = 1.0,
    width: int = 640,
) -> Path:
    """Extract a thumbnail from video at a given timestamp.

    Args:
        video_path: Source video.
        output_path: Output image path.
        timestamp_sec: Position in the video (seconds).
        width: Thumbnail width (height auto-scaled).

    Returns:
        Path to the thumbnail.
    """
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-ss", str(timestamp_sec),
        "-i", str(video_path),
        "-vf", f"scale={width}:-1",
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise ExtractionError(f"Thumbnail failed: {proc.stderr[:300]}")
    if not output_path.exists():
        raise ExtractionError("Thumbnail output not found")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 14. Frame mosaic / contact sheet
# ─────────────────────────────────────────────────────────────────────
def create_contact_sheet(
    frame_paths: Sequence[Path],
    output_path: Path,
    columns: int = 4,
    tile_width: int = 320,
) -> Path:
    """Create a contact sheet (mosaic) from a list of frames.

    Args:
        frame_paths: Ordered list of frame image paths.
        output_path: Output image path.
        columns: Number of columns in the grid.
        tile_width: Width of each tile (height auto-scaled).

    Returns:
        Path to the contact sheet image.
    """
    if not frame_paths:
        raise ExtractionError("No frames provided for contact sheet")
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(frame_paths)
    cols = min(columns, n)
    rows = (n + cols - 1) // cols
    # Build ffmpeg complex filter
    inputs: list[str] = []
    filter_parts: list[str] = []
    for i, fp in enumerate(frame_paths):
        inputs.extend(["-i", str(fp)])
        filter_parts.append(f"[{i}:v]scale={tile_width}:-1:force_original_aspect_ratio=decrease,"
                            f"pad={tile_width}:{tile_width}*ih/iw:(ow-iw)/2:(oh-ih)/2[t{i}];")
    # Build xstack layout
    layout_parts: list[str] = []
    for i in range(n):
        col = i % cols
        row = i // cols
        layout_parts.append(f"{col}*{tile_width}|{row}*{tile_width}")
    # Pad with null inputs if n < rows*cols
    pad_count = rows * cols - n
    for j in range(pad_count):
        idx = n + j
        inputs.extend(["-f", "lavfi", "-i", f"color=black:s={tile_width}x{tile_width}:d=1"])
        filter_parts.append(f"[{idx}:v]setsar=1[t{idx}];")
        col = (n + j) % cols
        row = (n + j) // cols
        layout_parts.append(f"{col}*{tile_width}|{row}*{tile_width}")
    total = n + pad_count
    input_labels = "".join(f"[t{i}]" for i in range(total))
    filter_str = "".join(filter_parts) + f"{input_labels}xstack=inputs={total}:layout={'|'.join(layout_parts)}[out]"
    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-q:v", "2",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise ExtractionError(f"Contact sheet failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 15. Video info / stats
# ─────────────────────────────────────────────────────────────────────
def get_video_info(video_path: Path) -> dict:
    """Get detailed video information using ffprobe.

    Returns:
        Dict with keys: duration, width, height, fps, codec, audio_codec,
        bitrate, file_size_mb, format_name.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise ExtractionError("ffprobe not found on PATH")
    cmd = [
        ffprobe, "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise ExtractionError(f"ffprobe failed: {proc.stderr[:200]}")
    data = json.loads(proc.stdout)
    info: dict = {}
    fmt = data.get("format", {})
    info["duration"] = float(fmt.get("duration", 0))
    info["bitrate"] = int(fmt.get("bit_rate", 0))
    info["format_name"] = fmt.get("format_long_name", "")
    info["file_size_mb"] = round(int(fmt.get("size", 0)) / (1024 * 1024), 2)
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            info["width"] = int(s.get("width", 0))
            info["height"] = int(s.get("height", 0))
            info["codec"] = s.get("codec_name", "")
            r = s.get("r_frame_rate", "0/1")
            parts = r.split("/")
            if len(parts) == 2 and int(parts[1]) > 0:
                info["fps"] = round(int(parts[0]) / int(parts[1]), 2)
            else:
                info["fps"] = 0.0
        if s.get("codec_type") == "audio" and "audio_codec" not in info:
            info["audio_codec"] = s.get("codec_name", "")
            info["audio_sample_rate"] = int(s.get("sample_rate", 0))
            info["audio_channels"] = int(s.get("channels", 0))
    return info


# ─────────────────────────────────────────────────────────────────────
# 16. Frame crop
# ─────────────────────────────────────────────────────────────────────
def crop_frame(
    image_path: Path,
    output_path: Path,
    x: int,
    y: int,
    width: int,
    height: int,
) -> Path:
    """Crop a rectangular region from a frame image.

    Args:
        image_path: Source image.
        output_path: Output image path.
        x: Left offset in pixels.
        y: Top offset in pixels.
        width: Crop width.
        height: Crop height.

    Returns:
        Path to the cropped image.
    """
    if width <= 0 or height <= 0:
        raise ExtractionError("Crop width and height must be positive")
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-i", str(image_path),
        "-vf", f"crop={width}:{height}:{x}:{y}",
        "-q:v", "2",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise ExtractionError(f"Crop failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 17. Reverse video
# ─────────────────────────────────────────────────────────────────────
def reverse_video(
    video_path: Path,
    output_path: Path,
) -> Path:
    """Reverse video playback (video + audio).

    Args:
        video_path: Source video.
        output_path: Output video path.

    Returns:
        Path to the reversed video.
    """
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vf", "reverse",
        "-af", "areverse",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise ExtractionError(f"Reverse failed: {proc.stderr[:300]}")
    return output_path


# ─────────────────────────────────────────────────────────────────────
# 18. Extract all frames (full FPS)
# ─────────────────────────────────────────────────────────────────────
def extract_all_frames(
    video_path: Path,
    output_dir: Path,
    max_frames: int = 0,
) -> list[Path]:
    """Extract every frame from video at original FPS.

    Args:
        video_path: Source video.
        output_dir: Directory to save frames.
        max_frames: Limit number of frames (0 = unlimited).

    Returns:
        List of extracted frame paths.
    """
    ffmpeg = _require_ffmpeg()
    output_dir.mkdir(parents=True, exist_ok=True)
    vframes_args = ["-vframes", str(max_frames)] if max_frames > 0 else []
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        *vframes_args,
        "-q:v", "2",
        str(output_dir / "frame_%06d.jpg"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise ExtractionError(f"Frame extraction failed: {proc.stderr[:300]}")
    frames = sorted(output_dir.glob("frame_*.jpg"))
    return frames


# ─────────────────────────────────────────────────────────────────────
# 19. Frame deduplication
# ─────────────────────────────────────────────────────────────────────
def find_duplicate_frames(
    frame_paths: Sequence[Path],
    threshold: float = 0.95,
) -> list[tuple[int, int, float]]:
    """Find near-duplicate frame pairs by comparing file hashes or pixel similarity.

    Args:
        frame_paths: List of frame image paths.
        threshold: Similarity threshold (0.0–1.0). Higher = stricter.

    Returns:
        List of (index_a, index_b, similarity) tuples for duplicates.
    """
    import hashlib
    duplicates: list[tuple[int, int, float]] = []
    hashes: list[tuple[int, str]] = []
    for i, fp in enumerate(frame_paths):
        h = hashlib.sha256(fp.read_bytes()).hexdigest()
        hashes.append((i, h))
    # Exact duplicates
    seen: dict[str, int] = {}
    for idx, h in hashes:
        if h in seen:
            duplicates.append((seen[h], idx, 1.0))
        else:
            seen[h] = idx
    # If OpenCV available, check near-duplicates via histogram comparison
    try:
        import cv2
        import numpy as np  # noqa: F401 — used implicitly by cv2 histogram ops
        histograms: list[tuple[int, object]] = []
        for i, fp in enumerate(frame_paths):
            img = cv2.imread(str(fp))
            if img is not None:
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
                cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
                histograms.append((i, hist))
        already = {(a, b) for a, b, _ in duplicates}
        for i in range(len(histograms)):
            for j in range(i + 1, len(histograms)):
                idx_a, hist_a = histograms[i]
                idx_b, hist_b = histograms[j]
                if (idx_a, idx_b) in already:
                    continue
                sim = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
                if sim >= threshold:
                    duplicates.append((idx_a, idx_b, round(sim, 4)))
    except ImportError:
        pass  # cv2 not available — only exact duplicates reported
    return duplicates


# ─────────────────────────────────────────────────────────────────────
# 20. Merge (concatenate) videos
# ─────────────────────────────────────────────────────────────────────
def merge_videos(
    video_paths: Sequence[Path],
    output_path: Path,
) -> Path:
    """Concatenate multiple videos into one using ffmpeg concat demuxer.

    All videos should have the same codec/resolution for seamless merging.

    Args:
        video_paths: Ordered list of video file paths.
        output_path: Output video path.

    Returns:
        Path to the merged video.
    """
    if len(video_paths) < 2:
        raise ExtractionError("Need at least 2 videos to merge")
    ffmpeg = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output_path.parent / "_concat_list.txt"
    lines = [f"file '{p}'" for p in video_paths]
    concat_file.write_text("\n".join(lines), encoding="utf-8")
    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    concat_file.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise ExtractionError(f"Merge failed: {proc.stderr[:300]}")
    return output_path
