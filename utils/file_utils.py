"""Output folder helpers — no Qt imports."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.models import JobResult


def create_output_dir(base_dir: Path, video_id: str = "pending") -> Path:
    """Create a timestamped output subdirectory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in video_id)
    folder = Path(base_dir) / f"{safe_id}_{ts}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_results_json(output_root: Path, result: JobResult) -> Path:
    """Write results.json to output_root."""
    config = result.config
    frames_data = [
        {
            "index": f.index,
            "timestamp_sec": f.timestamp_sec,
            "timestamp_label": f.timestamp_label,
            "image_file": f"frames/{f.image_path.name}",
            "prompt_file": f"prompts/{f.image_path.stem}.txt",
            "prompt": f.prompt,
        }
        for f in result.frames
    ]

    payload = {
        "schema_version": "1.0",
        "video_url": config.url,
        "video_id": result.video_id,
        "video_title": result.video_title,
        "extracted_at": result.completed_at,
        "interval_seconds": config.interval_sec,
        "prompt_type": config.prompt_type,
        "frame_count": len(result.frames),
        "frames": frames_data,
    }

    out = output_root / "results.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def write_summary_md(output_root: Path, result: JobResult) -> Path:
    """Write a Markdown summary suitable for Obsidian/Notion."""
    lines = [
        f"# {result.video_title}",
        "",
        f"- **URL:** {result.config.url}",
        f"- **Video ID:** {result.video_id}",
        f"- **Extracted at:** {result.completed_at}",
        f"- **Interval:** {result.config.interval_sec}s",
        f"- **Prompt type:** {result.config.prompt_type}",
        f"- **Frame count:** {len(result.frames)}",
        "",
        "## Frames",
        "",
        "| # | Time | Thumbnail | Prompt (preview) |",
        "|---|------|-----------|-----------------|",
    ]

    for f in result.frames:
        thumb = f"frames/{f.image_path.name}"
        preview = f.prompt[:80].replace("|", "\\|")
        if len(f.prompt) > 80:
            preview += "…"
        lines.append(f"| {f.index} | {f.timestamp_label} | ![]({thumb}) | {preview} |")

    lines.append("")
    out = output_root / "summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
