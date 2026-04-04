"""QSettings wrapper for app preferences."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

_ORG = "AIFramePrompt"
_APP = "YouTubePromptGen"


class AppSettings:
    def __init__(self) -> None:
        self._qs = QSettings(_ORG, _APP)

    # --- API key ---
    def get_api_key(self) -> str:
        return self._qs.value("api_key", "", type=str)

    def set_api_key(self, value: str) -> None:
        self._qs.setValue("api_key", value)

    # --- Interval ---
    def get_interval(self) -> int:
        return self._qs.value("interval", 5, type=int)

    def set_interval(self, value: int) -> None:
        self._qs.setValue("interval", value)

    # --- Prompt type ---
    def get_prompt_type(self) -> str:
        return self._qs.value("prompt_type", "image", type=str)

    def set_prompt_type(self, value: str) -> None:
        self._qs.setValue("prompt_type", value)

    # --- Output dir ---
    def get_output_dir(self) -> Path:
        default = str(Path.home() / "ai-shot-cutter" / "output")
        return Path(self._qs.value("output_dir", default, type=str))

    def set_output_dir(self, value: Path) -> None:
        self._qs.setValue("output_dir", str(value))

    # --- Max frames ---
    def get_max_frames(self) -> int:
        return self._qs.value("max_frames", 0, type=int)

    def set_max_frames(self, value: int) -> None:
        self._qs.setValue("max_frames", value)

    # --- Theme ---
    def get_theme(self) -> str:
        return self._qs.value("theme", "dark", type=str)

    def set_theme(self, value: str) -> None:
        self._qs.setValue("theme", value)

    def sync(self) -> None:
        self._qs.sync()
