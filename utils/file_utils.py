"""Output folder helpers — no Qt imports."""
from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from pathlib import Path

from core.models import FrameResult, JobResult


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


# ------------------------------------------------------------------
# Feature: Export HTML report
# ------------------------------------------------------------------
def write_html_report(
    output_path: Path, frames: list[FrameResult], title: str = "Frame Prompts"
) -> Path:
    """Generate a self-contained HTML gallery with thumbnails + prompts."""
    safe_title = html.escape(title)
    rows: list[str] = []
    for f in frames:
        safe_prompt = html.escape(f.prompt)
        img_src = html.escape(str(f.image_path))
        rows.append(
            f'<div class="card">'
            f'<img src="file:///{img_src}" alt="frame {f.index}" />'
            f'<div class="info">'
            f'<span class="ts">{html.escape(f.timestamp_label)}</span>'
            f'<p>{safe_prompt}</p>'
            f'</div></div>'
        )

    content = "\n".join(rows)
    page = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{safe_title}</title>"
        "<style>"
        "body{font-family:system-ui;background:#1e1e2e;color:#cdd6f4;margin:20px}"
        "h1{text-align:center}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}"
        ".card{background:#313244;border-radius:10px;overflow:hidden}"
        ".card img{width:100%;height:auto}"
        ".info{padding:10px}"
        ".ts{color:#89b4fa;font-size:12px;font-weight:600}"
        "p{font-size:12px;line-height:1.4}"
        "</style></head><body>"
        f"<h1>{safe_title}</h1>"
        f'<div class="grid">{content}</div>'
        "</body></html>"
    )

    output_path.write_text(page, encoding="utf-8")
    return output_path


# ------------------------------------------------------------------
# Feature: Export CSV
# ------------------------------------------------------------------
def write_csv(output_path: Path, frames: list[FrameResult]) -> Path:
    """Export frame data as CSV (index, timestamp, prompt, image_path)."""
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["index", "timestamp", "prompt", "image_path"])
        for f in frames:
            writer.writerow([f.index, f.timestamp_label, f.prompt, str(f.image_path)])
    return output_path
