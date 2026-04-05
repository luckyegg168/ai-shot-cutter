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

    # --- Resolution ---
    def get_resolution(self) -> str:
        return self._qs.value("resolution", "1080", type=str)

    def set_resolution(self, value: str) -> None:
        self._qs.setValue("resolution", value)

    # --- Language ---
    def get_language(self) -> str:
        return self._qs.value("language", "zh_TW", type=str)

    def set_language(self, value: str) -> None:
        self._qs.setValue("language", value)
        self._qs.sync()

    # --- Local model ---
    def get_use_local_model(self) -> bool:
        return self._qs.value("use_local_model", False, type=bool)

    def set_use_local_model(self, value: bool) -> None:
        self._qs.setValue("use_local_model", value)

    def get_local_model_url(self) -> str:
        return self._qs.value("local_model_url", "", type=str)

    def set_local_model_url(self, value: str) -> None:
        self._qs.setValue("local_model_url", value)

    def get_model_name(self) -> str:
        return self._qs.value("model_name", "", type=str)

    def set_model_name(self, value: str) -> None:
        self._qs.setValue("model_name", value)

    # --- Custom system prompt ---
    def get_custom_system_prompt(self) -> str:
        return self._qs.value("custom_system_prompt", "", type=str)

    def set_custom_system_prompt(self, value: str) -> None:
        self._qs.setValue("custom_system_prompt", value)

    # --- Blur threshold ---
    def get_blur_threshold(self) -> float:
        return float(self._qs.value("blur_threshold", 0.0, type=float))

    def set_blur_threshold(self, value: float) -> None:
        self._qs.setValue("blur_threshold", value)

    def sync(self) -> None:
        self._qs.sync()
