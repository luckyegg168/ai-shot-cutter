# YouTube AI Frame Prompt Generator — Implementation Plan

## Project Overview

A pure desktop GUI application (PySide6/Qt6) that:
1. Accepts a YouTube URL and extraction interval
2. Downloads the video via yt-dlp
3. Extracts frames every N seconds via ffmpeg
4. Sends each frame to GPT-4o Vision to generate high-quality text-to-image / text-to-video prompts
5. Displays real-time progress, frame gallery, and structured output

---

## Phase 0: Environment & Scaffold (Day 1)

### Goals
- Set up project structure
- Verify all dependencies installable

### Tasks
- [ ] Create directory structure (see spec.md)
- [ ] Create `requirements.txt`
- [ ] Create `pyproject.toml` (optional, for packaging)
- [ ] Verify: `pip install PySide6 yt-dlp openai tqdm`
- [ ] Verify: `ffmpeg` available on PATH
- [ ] Write a smoke-test script that imports all modules

### Dependencies
```
PySide6>=6.6.0
yt-dlp>=2024.1.0
openai>=1.0.0
tqdm>=4.66.0
```

---

## Phase 1: Core Business Logic (Day 1–2)

### Goals
- Backend logic fully working and testable without GUI

### Modules to build
| Module | Responsibility |
|--------|---------------|
| `core/downloader.py` | Wrap yt-dlp; download video to temp dir |
| `core/extractor.py` | Wrap ffmpeg; extract frames at interval |
| `core/vision.py` | Call GPT-4o Vision; return prompt string |
| `core/pipeline.py` | Orchestrate download → extract → vision loop |
| `core/models.py` | Dataclasses: `FrameResult`, `JobConfig`, `JobResult` |

### Key interfaces (pseudo-code)
```python
# downloader.py
def download_video(url: str, output_dir: Path, progress_cb: Callable) -> Path: ...

# extractor.py
def extract_frames(video_path: Path, interval_sec: int, output_dir: Path) -> list[Path]: ...

# vision.py
def analyze_frame(image_path: Path, api_key: str, prompt_type: str) -> str: ...

# pipeline.py
class Pipeline:
    def run(self, config: JobConfig, on_progress: Callable, on_frame_done: Callable) -> JobResult: ...
```

### Acceptance criteria
- `download_video` returns a `.mp4` Path or raises `DownloadError`
- `extract_frames` returns sorted list of `frame_0001.jpg`, `frame_0002.jpg`, ...
- `analyze_frame` returns non-empty string prompt
- Unit tests pass with mocked yt-dlp / ffmpeg / openai

---

## Phase 2: Worker Thread (Day 2)

### Goals
- Wrap pipeline in `QThread` so GUI stays responsive

### Modules
| Module | Responsibility |
|--------|---------------|
| `workers/pipeline_worker.py` | `QThread` subclass wrapping `Pipeline.run` |

### Signals emitted by `PipelineWorker`
```python
progress_updated = Signal(int, int, str)   # current, total, message
frame_ready = Signal(str, str)             # image_path, prompt_text
job_finished = Signal(dict)               # full JobResult as dict
error_occurred = Signal(str)              # error message
```

### Acceptance criteria
- Worker can be started and cancelled
- All signals fire correctly under mocked pipeline
- No GUI freeze during long operations

---

## Phase 3: GUI — Main Window (Day 3)

### Goals
- Build the main application window with all panels

### Layout (3-panel)
```
┌────────────────────────────────────────────┐
│  [Input Panel]                              │
│  URL: ___________  Interval: __  API: ___  │
│  [Start]  [Stop]  [Open Output]            │
├──────────────────┬─────────────────────────┤
│  [Gallery Panel] │  [Prompt Panel]          │
│  Thumbnail grid  │  Selected frame prompt   │
│  (scrollable)    │  [Copy]  [Export JSON]   │
├────────────────────────────────────────────┤
│  [Log / Progress Panel]                     │
│  Progress bar  |  Log textarea              │
└────────────────────────────────────────────┘
```

### Widgets
| Widget | Class | File |
|--------|-------|------|
| Input panel | `InputPanel(QWidget)` | `ui/input_panel.py` |
| Gallery | `GalleryWidget(QScrollArea)` | `ui/gallery_widget.py` |
| Prompt viewer | `PromptPanel(QWidget)` | `ui/prompt_panel.py` |
| Log area | `LogPanel(QWidget)` | `ui/log_panel.py` |
| Main window | `MainWindow(QMainWindow)` | `ui/main_window.py` |
| Gallery card | `FrameCard(QFrame)` | `ui/frame_card.py` |

### Acceptance criteria
- Window launches without errors
- Input validation: URL non-empty, interval 1–300, API key non-empty
- Start button disabled while job running
- Stop button cancels worker and cleans up

---

## Phase 4: Gallery & Frame Card (Day 3–4)

### Goals
- Thumbnails appear in real-time as frames are processed

### FrameCard behavior
- Shows 160×90px thumbnail
- Shows first 80 chars of prompt below
- Clicking selects it → shows full prompt in PromptPanel
- Selected card has highlighted border

### GalleryWidget behavior
- Uses `QFlowLayout` (or `QGridLayout`) in a `QScrollArea`
- Auto-scrolls to newest card
- Cards added via `add_frame(image_path, prompt)` slot

### Acceptance criteria
- 20 cards render without lag
- Selecting a card updates PromptPanel immediately
- Gallery scrolls to newest card on add

---

## Phase 5: Output & Export (Day 4)

### Goals
- Save results to structured folder on disk

### Output folder structure
```
output/
  <video_id>_<timestamp>/
    frames/
      frame_0001.jpg
      frame_0002.jpg
      ...
    prompts/
      frame_0001.txt
      frame_0002.txt
      ...
    results.json
    summary.md
```

### `results.json` schema
```json
{
  "video_url": "...",
  "video_title": "...",
  "extracted_at": "ISO8601",
  "interval_seconds": 5,
  "frames": [
    {
      "index": 1,
      "timestamp_sec": 0,
      "image_file": "frames/frame_0001.jpg",
      "prompt": "..."
    }
  ]
}
```

### Acceptance criteria
- Output folder created automatically
- `results.json` valid JSON, matches schema
- "Open Output" button opens folder in OS file explorer
- "Export JSON" button saves filtered results

---

## Phase 6: Polish & Error Handling (Day 5)

### Goals
- Robust error handling, settings persistence, UX polish

### Tasks
- [ ] Settings persistence via `QSettings` (API key, last interval, output dir)
- [ ] Error dialogs for: invalid URL, ffmpeg not found, API quota exceeded
- [ ] Graceful cancellation (stop download mid-way, clean temp files)
- [ ] Dark/light theme toggle (Qt stylesheet)
- [ ] App icon + window title
- [ ] About dialog

---

## Phase 7: Testing (Day 5–6)

### Test strategy
- Unit: core modules with mocked subprocesses and API
- Integration: pipeline end-to-end with a small real video (< 30s)
- GUI: smoke tests via `pytest-qt`

### Acceptance criteria (overall)
- 80%+ coverage on `core/` modules
- All happy-path and error-path tests pass
- No crashes on Cancel mid-operation

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| yt-dlp blocked by YouTube | Medium | Retry with cookies; document workaround |
| ffmpeg not on PATH (Windows) | Medium | Bundle ffmpeg or prompt user to install |
| GPT-4o rate limits | Medium | Add retry with backoff; expose delay setting |
| Large video (>1GB) fills disk | Low | Estimate size before download; warn user |
| Qt version incompatibility | Low | Pin `PySide6>=6.6` in requirements |

---

## Phase 3 — v1.1 Fixes & Features (Completed)

### Bug Fixes
- [x] **B-01** `styles.qss`: Replace `QWidget { background-color: transparent }` with `#1e1e2e`; transparent override on QLabel/QCheckBox/QRadioButton only
- [x] **B-02** `main_window.py`: Change `setSizes([160, 480, 200])` → `[330, 350, 120]`
- [x] **B-03** `input_panel.py`: Add `setVerticalSpacing(10)` + `setContentsMargins(14, 12, 14, 12)` to QFormLayout

### New Features
- [x] **F-01** API key eye toggle — `_eye_btn` QPushButton beside `_api_edit`
- [x] **F-02** Keyboard shortcuts — Ctrl+Enter / Esc / Ctrl+Shift+C via `MainWindow._setup_shortcuts()`
- [x] **F-03** Drag & drop URL — `dragEnterEvent` + `dropEvent` on `InputPanel`
- [x] **F-04** Live frame counter in status bar — `影格 X/Y · <message>` in `_on_progress`
- [x] **F-05** Collapsible input panel — `_collapse_btn` toggle above form group

## Phase 4 — v1.2 Code Quality & 10 New Features (Completed)

### Bug Fixes
- [x] **B-04** Ruff lint errors (27 issues) — semicolon compound statements, unused imports, f-string in tr() calls
- [x] **B-05** Cross-thread UI crash — regenerate prompt called QWidget methods from non-main thread; fixed with `Signal`-based marshalling (`_regen_done`, `_regen_error`)
- [x] **B-06** f-string inside `self.tr()` — 11 occurrences converted to `self.tr("…").replace("%1", val)` pattern for proper i18n extraction
- [x] **B-07** Hardcoded Chinese strings in `gallery_widget.py` — replaced with `self.tr()` calls

### New Features (10)
- [x] **F-06** Export HTML Report — `write_html_report()` in `file_utils.py`; dark-theme CSS grid gallery; wired via File → Export HTML Report menu
- [x] **F-07** Export CSV — `write_csv()` in `file_utils.py`; index/timestamp/prompt/image_path columns; wired via File → Export CSV menu
- [x] **F-08** Frame Zoom Viewer — `ui/zoom_viewer.py` `ZoomViewer(QDialog)` 900×650 modal; opens on gallery card double-click
- [x] **F-09** Auto-open Output Folder — settings checkbox + `get_auto_open_output()`/`set_auto_open_output()` in `AppSettings`; auto-calls `_open_output()` on job finish
- [x] **F-10** Home/End Gallery Navigation — `QShortcut(Home)` → `select_first()`, `QShortcut(End)` → `select_last()` on gallery
- [x] **F-11** Live Status Bar Frame Counter — `_on_progress` displays `Frame X/Y · <message>` via i18n
- [x] **F-12** Prompt History — `utils/prompt_history.py` JSON persistence (~/.ai-shot-cutter/prompt_history.json, 500-entry cap); View → Prompt History menu
- [x] **F-13** Duration Estimation — `_on_metadata` parses video duration and shows "Estimated frames: ~N (every Xs)" in status bar
- [x] **F-14** Live Theme Toggle — `SettingsPanel.theme_changed` signal → `_apply_theme_live()` reads QSS and applies via `QApplication.setStyleSheet()` without restart
- [x] **F-15** Gallery Search/Filter — QLineEdit filter bar with clear button; filters cards by prompt text match in real-time

### i18n
- [x] Updated `i18n/zh_TW.json` and `i18n/en_US.json` with all new translatable strings (20+ entries)

### Verification
- [x] `ruff check .` — All checks passed (0 errors)
- [x] `pytest tests/ -x` — 53/53 tests passed

---

## Phase 5 — v1.3 UI Overhaul + 10 New Features

### UI Improvements
- [x] Tab icons with emoji prefix (⚙ Job Settings / 🔧 Tools / ⚙ Settings)
- [x] Gallery empty state label ("🎞 No frames yet")
- [x] Gallery jump-to-frame spinbox (#N)
- [x] QDoubleSpinBox styles added to `styles.qss`

### New Features (10)
- [x] **F-16** Toast Notifications — `ui/toast.py` `Toast(QLabel)` overlay; info/warning/error levels; auto-fade via `QPropertyAnimation`
- [x] **F-17** Frame Favorites — ⭐ star button on each `FrameCard`; `toggled_favorite` signal; `is_favorite` property; starred-only filter checkbox in gallery toolbar
- [x] **F-18** Clipboard URL Auto-detect — `changeEvent` on `MainWindow` detects YouTube URLs in clipboard on window activate; shows dismissable banner in `InputPanel`
- [x] **F-19** Prompt Char/Word Counter — `_counter_label` below `_prompt_edit` in `PromptPanel`; updates on `textChanged`
- [x] **F-20** Keyboard Shortcuts Help — Ctrl+/ shortcut + Help menu item; `_show_shortcuts_help()` dialog listing all shortcuts
- [x] **F-21** Gallery Sort — `_sort_combo` in gallery toolbar; options: Frame Order / Timestamp ▲ / Timestamp ▼ / Prompt Length; `_apply_sort()` sorts `_cards` in-place + `_relayout()`
- [x] **F-22** Recent URLs — `QComboBox` above URL textarea; `AppSettings.get_recent_urls()` / `add_recent_url()`; last 10, dedup; populated on `_load_settings()`
- [x] **F-23** Extended Prompt Types — 4 new types in `core/vision.py`: character, landscape, product, architecture; 4 new `addItem()` calls in `InputPanel._prompt_combo`
- [x] **F-24** Session Summary Dialog — after successful job: frame count, elapsed time, avg/max prompt length; `[Open Output Folder]` + `[Close]` buttons
- [x] **F-25** Always on Top — View → Always on Top checkable QAction; `setWindowFlag(WindowStaysOnTopHint)`; persisted via `AppSettings.get/set_always_on_top()`

### Settings additions
- [x] `AppSettings.get_recent_urls()` / `add_recent_url()` — capped at 10, dedup
- [x] `AppSettings.get_always_on_top()` / `set_always_on_top()` — bool, default False

### Verification
- [x] `ruff check ui/ utils/settings.py` — All checks passed (0 errors)
- [x] `pytest tests/ -x` — 53/53 tests passed
- [x] `git commit` — feat(ui): v1.3 — 10 new features + UI improvements
