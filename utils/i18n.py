"""i18n — JSON-based translator for PySide6 without needing .qm compilation."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTranslator

_I18N_DIR = Path(__file__).parent.parent / "i18n"

# Supported languages: locale code → display name
SUPPORTED_LANGUAGES: dict[str, str] = {
    "zh_TW": "繁體中文",
    "en_US": "English",
}


class _JsonTranslator(QTranslator):
    """QTranslator subclass that serves translations from a Python dict."""

    def __init__(self, translations: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self._dict = translations

    def translate(
        self,
        context: str,
        source_text: str,
        disambiguation: str | None = None,
        n: int = -1,
    ) -> str:
        return self._dict.get(source_text, "")  # "" → Qt falls back to source_text


def load_translator(
    app: QCoreApplication,
    lang: str = "zh_TW",
) -> _JsonTranslator | None:
    """Install a JSON translator for *lang* onto *app*.

    If the JSON file for *lang* does not exist, returns None and the app
    renders all strings in English (the source language).
    """
    json_path = _I18N_DIR / f"{lang}.json"
    if not json_path.exists():
        return None

    try:
        data: dict[str, str] = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    translator = _JsonTranslator(data)
    app.installTranslator(translator)
    return translator
