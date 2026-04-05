"""Pipeline orchestrator — pure Python, no Qt imports."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .downloader import download_video
from .extractor import extract_frames, get_video_duration
from .models import DownloadError, ExtractionError, FrameResult, JobConfig, JobResult, VisionError
from .vision import analyze_frame

from utils.file_utils import create_output_dir, write_results_json, write_summary_md


class Pipeline:
    """Orchestrates download → extract → vision for a single job."""

    def run(
        self,
        config: JobConfig,
        on_progress: Callable[[int, int, str], None],
        on_frame_done: Callable[[FrameResult], None],
        stop_event: threading.Event,
    ) -> JobResult:
        """Run the full pipeline.

        Args:
            config: Job configuration.
            on_progress: Callback(current, total, message).
            on_frame_done: Callback(FrameResult) after each frame is analysed.
            stop_event: Set this to request cancellation.

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

            total = len(raw_frames)
            if total == 0:
                result.error_message = "No frames extracted"
                return result

            # --- Step 4: vision loop ---
            duration_map = _build_timestamp_map(raw_frames, config.interval_sec)

            for i, frame_path in enumerate(raw_frames, start=1):
                if stop_event.is_set():
                    result.error_message = "Job cancelled by user"
                    break

                on_progress(i - 1, total, f"Analyzing frame {i}/{total}…")

                try:
                    prompt = analyze_frame(frame_path, config.api_key, config.prompt_type)
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
