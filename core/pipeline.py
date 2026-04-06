"""Pipeline orchestrator — pure Python, no Qt imports.

Flow:
  1. Create output directory
  2. Download video
  3. Extract frames → save intermediate manifest
  4. Vision analysis (per-frame) → save prompts
  5. Write final results (JSON + summary.md)
"""
from __future__ import annotations

import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .downloader import download_video
from .extractor import extract_frames, get_video_duration
from .models import DownloadError, ExtractionError, FrameResult, JobConfig, JobResult, VisionError
from .vision import analyze_frame

from utils.file_utils import create_output_dir, write_results_json, write_summary_md


def _get_video_metadata(video_path: Path) -> dict:
    """Return a dict with duration, width, height, fps from ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", str(video_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return {}
        data = json.loads(proc.stdout)
        meta: dict = {}
        fmt = data.get("format", {})
        meta["duration"] = float(fmt.get("duration", 0))
        meta["format_name"] = fmt.get("format_long_name", "")
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                meta["width"] = int(s.get("width", 0))
                meta["height"] = int(s.get("height", 0))
                r_frame = s.get("r_frame_rate", "0/1")
                parts = r_frame.split("/")
                if len(parts) == 2 and int(parts[1]) > 0:
                    meta["fps"] = round(int(parts[0]) / int(parts[1]), 2)
                else:
                    meta["fps"] = 0.0
                meta["codec"] = s.get("codec_name", "")
                break
        return meta
    except Exception:
        return {}


def _compute_blur_score(image_path: Path) -> float:
    """Compute Laplacian variance as a blur score. Higher = sharper."""
    try:
        import cv2
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 999.0  # can't read → treat as sharp (don't filter)
        return float(cv2.Laplacian(img, cv2.CV_64F).var())
    except ImportError:
        return 999.0  # cv2 not installed → skip filtering


class Pipeline:
    """Orchestrates download → extract → vision for a single job."""

    def run(
        self,
        config: JobConfig,
        on_progress: Callable[[int, int, str], None],
        on_frame_done: Callable[[FrameResult], None],
        stop_event: threading.Event,
        on_metadata: Callable[[dict], None] | None = None,
    ) -> JobResult:
        """Run the full pipeline.

        Args:
            config: Job configuration.
            on_progress: Callback(current, total, message).
            on_frame_done: Callback(FrameResult) after each frame is analysed.
            stop_event: Set this to request cancellation.
            on_metadata: Optional callback(dict) with video metadata.

        Returns:
            JobResult with all processed frames (may be partial on cancel).
        """
        result = JobResult(
            config=config,
            video_title="",
            video_id="",
        )

        try:
            # --- Step 1: prepare output directory ---
            output_root = create_output_dir(config.output_dir, video_id="pending")

            # --- Step 2: download ---
            on_progress(0, 100, "Downloading...")
            video_path = download_video(
                config.url,
                output_root,
                progress_cb=lambda pct, spd, eta: on_progress(pct, 100, f"Downloading… {spd} ETA {eta}"),
                resolution=config.resolution,
            )

            # Extract video id from filename stem
            video_id = video_path.stem
            result.video_id = video_id
            result.video_title = video_id   # best effort; yt-dlp may enrich later

            # Rename directory to include actual video id
            named_dir = config.output_dir / _make_folder_name(video_id)
            if not named_dir.exists():
                output_root.rename(named_dir)
                output_root = named_dir
            else:
                output_root = named_dir
            # Update video_path to reflect the renamed directory
            video_path = output_root / video_path.name

            # --- Step 2.5: extract video metadata ---
            metadata = _get_video_metadata(video_path)
            metadata["video_path"] = str(video_path)
            if on_metadata and metadata:
                on_metadata(metadata)

            frames_dir = output_root / "frames"
            prompts_dir = output_root / "prompts"
            frames_dir.mkdir(exist_ok=True)
            prompts_dir.mkdir(exist_ok=True)

            if stop_event.is_set():
                result.error_message = "Cancelled before frame extraction"
                return result

            # --- Step 3: extract frames ---
            on_progress(0, 1, "Extracting frames...")
            raw_frames = extract_frames(video_path, config.interval_sec, frames_dir)

            # Apply max_frames limit
            if config.max_frames > 0:
                raw_frames = raw_frames[: config.max_frames]

            # Apply blur filter (skip blurry frames)
            if config.blur_threshold > 0:
                filtered: list[Path] = []
                for fp in raw_frames:
                    score = _compute_blur_score(fp)
                    if score >= config.blur_threshold:
                        filtered.append(fp)
                    else:
                        on_progress(0, 1, f"Skipped blurry frame: {fp.name} (score={score:.1f})")
                raw_frames = filtered

            total = len(raw_frames)
            if total == 0:
                result.error_message = "No frames extracted"
                return result

            # --- Step 3.5: save intermediate frame manifest ---
            on_progress(0, total, "Saving frame manifest...")
            manifest = {
                "video_id": video_id,
                "video_path": str(video_path),
                "frame_count": total,
                "interval_sec": config.interval_sec,
                "frames": [str(f) for f in raw_frames],
            }
            manifest_path = output_root / "frames_manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            # --- Step 4: vision loop ---
            duration_map = _build_timestamp_map(raw_frames, config.interval_sec)

            for i, frame_path in enumerate(raw_frames, start=1):
                if stop_event.is_set():
                    result.error_message = "Job cancelled by user"
                    break

                on_progress(i - 1, total, f"Analyzing frame {i}/{total}…")

                try:
                    prompt = analyze_frame(
                        frame_path,
                        config.api_key,
                        config.prompt_type,
                        use_local_model=config.use_local_model,
                        local_model_url=config.local_model_url,
                        model_name=config.model_name,
                        custom_system_prompt=config.custom_system_prompt,
                    )
                except VisionError as exc:
                    prompt = f"[Vision error: {exc}]"

                # Save prompt file
                prompt_file = prompts_dir / (frame_path.stem + ".txt")
                prompt_file.write_text(prompt, encoding="utf-8")

                frame_result = FrameResult(
                    index=i,
                    timestamp_sec=duration_map.get(frame_path.name, (i - 1) * config.interval_sec),
                    image_path=frame_path,
                    prompt=prompt,
                )
                result.frames.append(frame_result)
                on_frame_done(frame_result)
                on_progress(i, total, f"Analyzing frame {i}/{total}…")

            # --- Step 5: write outputs ---
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.success = not bool(result.error_message)
            write_results_json(output_root, result)
            write_summary_md(output_root, result)

        except (DownloadError, ExtractionError) as exc:
            result.error_message = str(exc)
            result.success = False
        except Exception as exc:
            result.error_message = f"Unexpected error: {exc}"
            result.success = False

        return result


def _make_folder_name(video_id: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in video_id)
    return f"{safe_id}_{ts}"


def _build_timestamp_map(frames: list[Path], interval_sec: int) -> dict[str, float]:
    """Map frame filename → estimated timestamp in seconds."""
    mapping: dict[str, float] = {}
    for i, p in enumerate(frames):
        mapping[p.name] = i * interval_sec
    return mapping
