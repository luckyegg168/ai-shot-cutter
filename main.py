"""Entry point for YouTube AI Frame Prompt Generator."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("YouTubePromptGen")
    app.setOrganizationName("AIFramePrompt")
    app.setApplicationVersion("1.0.0")

    # Load stylesheet
    qss_path = _ROOT / "ui" / "styles.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    from utils.settings import AppSettings
    from ui.main_window import MainWindow

    settings = AppSettings()
    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
