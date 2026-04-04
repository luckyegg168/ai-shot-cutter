"""Data models for ai-shot-cutter (immutable dataclasses, no Qt)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class JobConfig:
    url: str
    interval_sec: int          # 1–300
    api_key: str
    output_dir: Path
    prompt_type: str           # "image" | "video"
    max_frames: int = 0        # 0 = unlimited


@dataclass(frozen=True)
class FrameResult:
    index: int
    timestamp_sec: float
    image_path: Path
    prompt: str

    @property
    def timestamp_label(self) -> str:
        total = int(self.timestamp_sec)
        m, s = divmod(total, 60)
        return f"{m}:{s:02d}"


@dataclass
class JobResult:
    config: JobConfig
    video_title: str
    video_id: str
    frames: list[FrameResult] = field(default_factory=list)
    completed_at: str = ""     # ISO 8601
    success: bool = False
    error_message: str = ""


class DownloadError(Exception):
    pass


class ExtractionError(Exception):
    pass


class VisionError(Exception):
    pass
