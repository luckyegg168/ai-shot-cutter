"""Prompt history — persists prompt generation history as JSON."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_HISTORY_FILE = Path.home() / ".ai-shot-cutter" / "prompt_history.json"
_MAX_ENTRIES = 500


def _ensure_dir() -> None:
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_history() -> list[dict]:
    """Load prompt history entries."""
    if not _HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def append_entry(
    url: str,
    frame_index: int,
    timestamp_label: str,
    prompt: str,
    prompt_type: str,
) -> None:
    """Append a single history entry (capped at _MAX_ENTRIES)."""
    _ensure_dir()
    entries = load_history()
    entries.append({
        "url": url,
        "frame_index": frame_index,
        "timestamp": timestamp_label,
        "prompt": prompt,
        "prompt_type": prompt_type,
        "created_at": datetime.now().isoformat(),
    })
    # Keep latest N entries
    entries = entries[-_MAX_ENTRIES:]
    _HISTORY_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clear_history() -> None:
    """Delete all history."""
    if _HISTORY_FILE.exists():
        _HISTORY_FILE.unlink()
