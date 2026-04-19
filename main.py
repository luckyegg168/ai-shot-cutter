"""Entry point for YouTube AI Frame Prompt Generator."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Startup dependency check ─────────────────────────────────
_MISSING: list[str] = []
for _pkg, _import in [
    ("yt-dlp", "yt_dlp"),
    ("openai", "openai"),
    ("tqdm", "tqdm"),
    ("PySide6", "PySide6"),
]:
    try:
        __import__(_import)
    except ImportError:
        _MISSING.append(_pkg)

if _MISSING:
    print("=" * 60, file=sys.stderr)
    print("ERROR: Missing required packages:", file=sys.stderr)
    for _p in _MISSING:
        print(f"  * {_p}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Run the launcher instead of plain python:", file=sys.stderr)
    print("  Windows:      run.bat", file=sys.stderr)
    print("  macOS/Linux:  ./run.sh", file=sys.stderr)
    print("  Or manually:  uv run python main.py", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("YouTubePromptGen")
    app.setOrganizationName("AIFramePrompt")
    app.setApplicationVersion("1.0.0")

    # Must create AppSettings BEFORE installing translator so we can read language pref
    from utils.settings import AppSettings
    settings = AppSettings()

    # Install i18n translator (default zh_TW)
    from utils.i18n import load_translator
    lang = settings.get_language()
    _translator = load_translator(app, lang)  # keep reference alive

    # Load stylesheet based on theme preference
    theme = settings.get_theme()
    if theme == "light":
        qss_path = _ROOT / "ui" / "styles_light.qss"
        if not qss_path.exists():
            qss_path = _ROOT / "ui" / "styles.qss"
    else:
        qss_path = _ROOT / "ui" / "styles.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    from ui.main_window import MainWindow

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
