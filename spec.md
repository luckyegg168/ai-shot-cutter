# YouTube AI Frame Prompt Generator — Technical Specification

## 1. Overview

**App name:** YouTube AI Frame Prompt Generator  
**Version:** 1.0.0  
**Platform:** Windows 10/11, macOS 13+, Ubuntu 22.04+  
**Runtime:** Python 3.11+, PySide6 6.6+

---

## 2. Directory Structure

```
ai-shot-cutter/
├── main.py                  # Entry point
├── requirements.txt
├── pyproject.toml
├── README.md
│
├── core/                    # Business logic (no Qt)
│   ├── __init__.py
│   ├── models.py            # Dataclasses
│   ├── downloader.py        # yt-dlp wrapper
│   ├── extractor.py         # ffmpeg wrapper
│   ├── vision.py            # OpenAI GPT-4o wrapper
│   └── pipeline.py          # Orchestration
│
├── workers/                 # Qt threading
│   ├── __init__.py
│   └── pipeline_worker.py   # QThread subclass
│
├── ui/                      # All Qt widgets
│   ├── __init__.py
│   ├── main_window.py
│   ├── input_panel.py
│   ├── gallery_widget.py
│   ├── frame_card.py
│   ├── prompt_panel.py
│   ├── log_panel.py
│   └── styles.qss           # Qt stylesheet
│
├── utils/
│   ├── __init__.py
│   ├── file_utils.py        # Output folder creation, path helpers
│   └── settings.py          # QSettings wrapper
│
├── assets/
│   └── icon.png
│
├── output/                  # Created at runtime
│
└── tests/
    ├── test_downloader.py
    ├── test_extractor.py
    ├── test_vision.py
    ├── test_pipeline.py
    └── test_gui_smoke.py
```

---

## 3. Data Models (`core/models.py`)

```python
@dataclass
class JobConfig:
    url: str
    interval_sec: int          # 1–300
    api_key: str
    output_dir: Path
    prompt_type: str           # "image" | "video"
    max_frames: int = 0        # 0 = unlimited

@dataclass
class FrameResult:
    index: int
    timestamp_sec: float
    image_path: Path
    prompt: str

@dataclass
class JobResult:
    config: JobConfig
    video_title: str
    video_id: str
    frames: list[FrameResult]
    completed_at: str          # ISO 8601
    success: bool
    error_message: str = ""
```

---

## 4. Core Module Specifications

### 4.1 `core/downloader.py`

**Function:** `download_video(url, output_dir, progress_cb) -> Path`

- Uses `yt-dlp` Python API (`YoutubeDL`)
- Format: best mp4 ≤ 1080p
- `progress_cb(percent: int, speed: str, eta: str)` called on each yt-dlp hook
- Returns path to downloaded `.mp4`
- Raises `DownloadError(message)` on failure

**yt-dlp options:**
```python
{
    "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
    "quiet": True,
    "progress_hooks": [hook],
}
```

---

### 4.2 `core/extractor.py`

**Function:** `extract_frames(video_path, interval_sec, output_dir) -> list[Path]`

- Calls `ffmpeg` as subprocess
- Command: `ffmpeg -i <video> -vf fps=1/<interval> -q:v 2 <output_dir>/frame_%04d.jpg`
- Returns sorted list of `.jpg` paths
- Raises `ExtractionError(message)` on ffmpeg failure

**Function:** `get_video_duration(video_path) -> float`
- Uses `ffprobe` to get duration in seconds

---

### 4.3 `core/vision.py`

**Function:** `analyze_frame(image_path, api_key, prompt_type) -> str`

- Encodes image as base64 data URL
- Calls `openai.chat.completions.create` with `model="gpt-4o"`
- System prompt varies by `prompt_type`:

  **image prompt:**
  ```
  You are an expert AI art director. Analyze this frame and generate a detailed, 
  high-quality text-to-image prompt suitable for Midjourney, DALL-E 3, or Stable Diffusion.
  Include: subject, composition, lighting, color palette, mood, style, camera angle, 
  and technical quality descriptors. Output only the prompt text, no explanations.
  ```

  **video prompt:**
  ```
  You are an expert AI video director. Analyze this frame and generate a detailed 
  text-to-video prompt suitable for Sora, Runway, or Pika Labs.
  Include: scene description, camera movement, subject action, lighting, atmosphere, 
  duration hint, and cinematic style. Output only the prompt text, no explanations.
  ```

- Returns prompt string (max 500 tokens)
- Raises `VisionError(message)` on API failure
- Implements exponential backoff (3 retries, 1s/2s/4s delays)

---

### 4.4 `core/pipeline.py`

**Class:** `Pipeline`

```python
class Pipeline:
    def run(
        self,
        config: JobConfig,
        on_progress: Callable[[int, int, str], None],
        on_frame_done: Callable[[FrameResult], None],
        stop_event: threading.Event,
    ) -> JobResult
```

**Execution sequence:**
1. Create output subdirectory: `output/<video_id>_<timestamp>/`
2. Download video → `on_progress(0, 100, "Downloading...")`
3. Extract frames → `on_progress(frame_i, total_frames, "Extracting...")`
4. For each frame:
   - Check `stop_event`; if set, stop and return partial result
   - Call `vision.analyze_frame`
   - Save prompt to `prompts/frame_XXXX.txt`
   - Call `on_frame_done(frame_result)`
   - `on_progress(i, total, f"Analyzing frame {i}/{total}")`
5. Write `results.json` and `summary.md`
6. Return `JobResult`

---

## 5. Worker Thread (`workers/pipeline_worker.py`)

```python
class PipelineWorker(QThread):
    progress_updated = Signal(int, int, str)   # current, total, message
    frame_ready      = Signal(object)          # FrameResult
    job_finished     = Signal(object)          # JobResult
    error_occurred   = Signal(str)             # error message

    def __init__(self, config: JobConfig): ...
    def run(self): ...
    def stop(self): ...   # sets stop_event, waits for thread to finish
```

- `run()` calls `Pipeline().run(...)`, emits signals on progress and frame done
- `stop()` sets `threading.Event`, which pipeline checks between frames

---

## 6. UI Specifications

### 6.1 `InputPanel`

| Control | Type | Validation |
|---------|------|-----------|
| YouTube URL | `QLineEdit` | Non-empty, starts with `http` |
| Interval (sec) | `QSpinBox` | 1–300, default 5 |
| OpenAI API Key | `QLineEdit` (password mode) | Non-empty, starts with `sk-` |
| Prompt Type | `QComboBox` | "Image Prompt" / "Video Prompt" |
| Max Frames | `QSpinBox` | 0–500, 0 = unlimited |
| [Start] | `QPushButton` | Disabled while running |
| [Stop] | `QPushButton` | Enabled only while running |
| [Open Output] | `QPushButton` | Always enabled if output exists |

**Validation:** `QLineEdit.textChanged` + `QSpinBox.valueChanged` → enable/disable Start button

---

### 6.2 `GalleryWidget`

- `QScrollArea` containing a `QWidget` with `QFlowLayout` (custom) or `QGridLayout` (3 columns)
- Cards added dynamically via `add_frame_card(image_path, prompt)` slot
- Auto-scrolls to bottom when new card added
- `card_selected = Signal(FrameResult)` emitted on click

---

### 6.3 `FrameCard`

- Fixed size: 180×140px
- Thumbnail: 160×90px, aspect-ratio preserved, `Qt.KeepAspectRatio`
- Prompt preview: first 80 chars, `QLabel` with word-wrap, small font
- Timestamp label: bottom-right, e.g. "0:32"
- Selected state: 2px blue border via stylesheet
- Mouse click: emit signal to parent

---

### 6.4 `PromptPanel`

- Frame number + timestamp header
- Full-size preview image (max 400×225px)
- Prompt text: `QTextEdit` (read-only)
- [Copy Prompt] button → `QApplication.clipboard().setText(prompt)`
- [Regenerate] button → re-calls vision API for selected frame

---

### 6.5 `LogPanel`

- `QProgressBar`: 0–100%, labeled "N/M frames"
- `QTextEdit` (read-only, monospace): appends timestamped log lines
- Color coding: green = success, red = error, yellow = warning
- [Clear Log] button

---

### 6.6 `MainWindow`

- Title: "YouTube AI Frame Prompt Generator"
- Min size: 1200×700px
- Layout: `QSplitter` (vertical) top=InputPanel, middle=`QSplitter`(horizontal) left=Gallery right=Prompt, bottom=LogPanel
- Menu bar: File → (Open Output, Export JSON, Exit), Help → (About)
- Status bar: shows current operation

---

## 7. Settings Persistence (`utils/settings.py`)

Saved via `QSettings("AIFramePrompt", "YouTubePromptGen")`:

| Key | Type | Default |
|-----|------|---------|
| `api_key` | str | "" |
| `interval` | int | 5 |
| `prompt_type` | str | "image" |
| `output_dir` | str | `~/ai-shot-cutter/output` |
| `max_frames` | int | 0 |
| `theme` | str | "dark" |

---

## 8. Output File Specification

### Folder naming
`<video_id>_<YYYYMMDD_HHMMSS>/`

### `results.json`
```json
{
  "schema_version": "1.0",
  "video_url": "https://...",
  "video_id": "dQw4w9WgXcQ",
  "video_title": "...",
  "extracted_at": "2026-04-05T12:00:00Z",
  "interval_seconds": 5,
  "prompt_type": "image",
  "frame_count": 42,
  "frames": [
    {
      "index": 1,
      "timestamp_sec": 0.0,
      "timestamp_label": "0:00",
      "image_file": "frames/frame_0001.jpg",
      "prompt_file": "prompts/frame_0001.txt",
      "prompt": "cinematic wide shot of..."
    }
  ]
}
```

### `summary.md`
- Markdown table of all frames with thumbnail reference and truncated prompt
- Suitable for Obsidian / Notion import

---

## 9. Error Handling Strategy

| Error | Where caught | User action |
|-------|-------------|-------------|
| Invalid URL | `InputPanel` on submit | Inline validation message |
| ffmpeg not found | `extractor.py` | Error dialog + link to install guide |
| yt-dlp download fail | `pipeline.py` | Error dialog with yt-dlp error text |
| OpenAI 401 (invalid key) | `vision.py` | Error dialog: "Check API key" |
| OpenAI 429 (rate limit) | `vision.py` | Auto-retry with backoff; log warning |
| OpenAI 5xx | `vision.py` | Retry 3x; then error dialog |
| Disk full | `pipeline.py` | Error dialog with disk usage info |
| User cancels | `PipelineWorker.stop()` | Partial results saved; "Job cancelled" log |

---

## 10. Acceptance Criteria (MVP)

| # | Criterion | How to verify |
|---|-----------|--------------|
| AC-01 | App launches on Windows 10+ | Run `python main.py` |
| AC-02 | Valid YouTube URL downloaded | Check output folder for `.mp4` |
| AC-03 | Frames extracted at correct interval | Count JPGs; verify timestamps |
| AC-04 | Each frame gets a non-empty prompt | Check `results.json` |
| AC-05 | Gallery shows thumbnails in real-time | Visual inspection |
| AC-06 | Stop button cancels job cleanly | No zombie processes |
| AC-07 | `results.json` matches schema | JSON schema validator |
| AC-08 | API key persists across restarts | Close + reopen app |
| AC-09 | App handles invalid URL gracefully | Enter "notaurl", click Start |
| AC-10 | Core module unit tests pass ≥80% | `pytest --cov=core` |

---

## 11. Dependencies

```txt
# requirements.txt
PySide6>=6.6.0
yt-dlp>=2024.1.0
openai>=1.30.0
tqdm>=4.66.0

# dev
pytest>=8.0.0
pytest-qt>=4.4.0
pytest-cov>=5.0.0
```

**External binaries required:**
- `ffmpeg` and `ffprobe` — must be on system PATH
- Recommended install: `winget install ffmpeg` (Windows) or `brew install ffmpeg` (macOS)
