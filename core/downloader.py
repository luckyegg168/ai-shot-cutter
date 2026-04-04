"""yt-dlp wrapper — pure Python, no Qt imports."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from .models import DownloadError


def _sanitize_url(url: str) -> str:
    """Basic URL validation — must start with https:// or http://."""
    url = url.strip()
    if not re.match(r"^https?://", url):
        raise DownloadError(f"Invalid URL format: {url!r}")
    return url


def download_video(
    url: str,
    output_dir: Path,
    progress_cb: Callable[[int, str, str], None] | None = None,
) -> Path:
    """Download a YouTube video using yt-dlp.

    Args:
        url: YouTube video URL.
        output_dir: Directory to save the video.
        progress_cb: Optional callback(percent, speed, eta).

    Returns:
        Path to the downloaded .mp4 file.

    Raises:
        DownloadError: On any yt-dlp failure.
    """
    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:
        raise DownloadError("yt-dlp is not installed. Run: pip install yt-dlp") from exc

    url = _sanitize_url(url)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded_path: list[Path] = []

    def _progress_hook(d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            percent = int(downloaded / total * 100)
            speed = d.get("speed_str", "?")
            eta = d.get("eta_str", "?")
            if progress_cb:
                progress_cb(percent, speed, eta)
        elif d.get("status") == "finished":
            filepath = d.get("filename") or d.get("info_dict", {}).get("_filename", "")
            if filepath:
                downloaded_path.append(Path(filepath))

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get("id", "unknown")
    except Exception as exc:
        raise DownloadError(str(exc)) from exc

    # Prefer path from hook; fall back to glob search
    if downloaded_path:
        candidate = downloaded_path[-1]
        if candidate.exists():
            return candidate

    # Fallback: find the file by video_id
    for p in sorted(output_dir.glob(f"{video_id}.*")):
        if p.suffix.lower() in (".mp4", ".mkv", ".webm"):
            return p

    raise DownloadError(f"Download completed but file not found in {output_dir}")
