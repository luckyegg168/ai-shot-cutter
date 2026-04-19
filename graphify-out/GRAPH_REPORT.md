# Graph Report - .  (2026-04-09)

## Corpus Check
- Corpus is ~20,396 words - fits in a single context window. You may not need a graph.

## Summary
- 447 nodes · 892 edges · 17 communities detected
- Extraction: 49% EXTRACTED · 51% INFERRED · 0% AMBIGUOUS · INFERRED: 457 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FrameResult` - 92 edges
2. `ExtractionError` - 52 edges
3. `AppSettings` - 49 edges
4. `MainWindow` - 43 edges
5. `ToolsPanel` - 40 edges
6. `SettingsPanel` - 30 edges
7. `GalleryWidget` - 29 edges
8. `InputPanel` - 27 edges
9. `JobConfig` - 21 edges
10. `FrameCard` - 21 edges

## Surprising Connections (you probably didn't know these)
- `ffmpeg wrapper — pure Python, no Qt imports.` --uses--> `ExtractionError`  [INFERRED]
  core\extractor.py → core\models.py
- `Return hwaccel names that ffmpeg reports as available.` --uses--> `ExtractionError`  [INFERRED]
  core\extractor.py → core\models.py
- `Return video duration in seconds using ffprobe.      Raises:         Extracti` --uses--> `ExtractionError`  [INFERRED]
  core\extractor.py → core\models.py
- `Extract one frame every interval_sec seconds using ffmpeg.      Args:` --uses--> `ExtractionError`  [INFERRED]
  core\extractor.py → core\models.py
- `FrameCard — thumbnail widget shown in GalleryWidget.` --uses--> `FrameResult`  [INFERRED]
  ui\frame_card.py → core\models.py

## Communities

### Community 0 - "Models & Tool Tests"
Cohesion: 0.04
Nodes (61): ExtractionError, _make_frame(), Tests for core/tools.py — video editing tools (no ffmpeg/cv2 required)., Create a minimal FrameResult with a dummy image file., TestAddTextWatermark, TestCompareFrames, TestDetectSceneChanges, TestExportGif (+53 more)

### Community 1 - "Video Downloader"
Cohesion: 0.06
Nodes (52): download_video(), yt-dlp wrapper — pure Python, no Qt imports., Basic URL validation — must start with https:// or http://., Download a YouTube video using yt-dlp.      Args:         url: YouTube video, _sanitize_url(), Exception, create_output_dir(), Output folder helpers — no Qt imports. (+44 more)

### Community 2 - "Log Panel UI"
Cohesion: 0.06
Nodes (14): LogPanel, LogPanel — progress bar + timestamped log output., Bottom panel: progress bar and scrolling log., MainWindow, QMainWindow, Smoke test: verify app window launches without crashing., MainWindow should open without error., Start button should be disabled until valid URL + API key provided. (+6 more)

### Community 3 - "Frame Card UI"
Cohesion: 0.08
Nodes (15): FrameCard, FrameCard — thumbnail widget shown in GalleryWidget., Fixed-size card showing a thumbnail, prompt preview, and timestamp., GalleryWidget, GalleryWidget — scrollable grid of FrameCards with adjustable columns., Select the previous card., Select the next card., Select the first card. (+7 more)

### Community 4 - "App Entry & Settings"
Cohesion: 0.06
Nodes (3): Entry point for YouTube AI Frame Prompt Generator., AppSettings, QSettings wrapper for app preferences.

### Community 5 - "Tools Panel"
Cohesion: 0.13
Nodes (3): ToolsPanel — 20 practical video editing tools in a dedicated tab., Video editing tools tab — 20 practical features., ToolsPanel

### Community 6 - "Settings Panel UI"
Cohesion: 0.14
Nodes (5): QWidget, _lbl(), SettingsPanel — dedicated settings page extracted from InputPanel., Dedicated settings tab — API keys, output, model, theme, language, etc., SettingsPanel

### Community 7 - "Prompt Panel"
Cohesion: 0.12
Nodes (9): _build_prompts_text(), PromptPanel, PromptPanel — shows full prompt text for a selected frame + batch actions., Display a frame result., Update prompt text for current frame (after regeneration)., Save the currently selected frame image to a user-chosen path., Copy all frame images to a user-chosen folder., Right panel: shows selected frame image + full prompt text. (+1 more)

### Community 8 - "Input Panel"
Cohesion: 0.13
Nodes (5): InputPanel, _lbl(), InputPanel — URL, interval, prompt type, max frames, start/stop controls.  Setti, Job configuration form — simplified to URL + job parameters + start/stop., Wire the SettingsPanel so InputPanel can read its values at job start.

### Community 9 - "Vision API Tests"
Cohesion: 0.3
Nodes (13): _cleanup_fake_openai(), _FakeAPIStatusError, _install_fake_openai(), _make_image(), Tests for core/vision.py, Create a minimal fake JPEG., Lightweight stand-in for openai.APIStatusError., Insert a fake 'openai' package into sys.modules and return the mock. (+5 more)

### Community 10 - "Downloader Tests"
Cohesion: 0.26
Nodes (8): _cleanup_fake_yt_dlp(), _install_fake_yt_dlp(), Tests for core/downloader.py, Insert a fresh MagicMock as the 'yt_dlp' module and return it., test_download_video_calls_progress_cb(), test_download_video_file_not_found_after_download(), test_download_video_success(), test_download_video_yt_dlp_error_raises_download_error()

### Community 11 - "i18n Translation"
Cohesion: 0.22
Nodes (6): _JsonTranslator, load_translator(), i18n — JSON-based translator for PySide6 without needing .qm compilation., QTranslator subclass that serves translations from a Python dict., Install a JSON translator for *lang* onto *app*.      If the JSON file for *la, QTranslator

### Community 12 - "Frame Extractor"
Cohesion: 0.31
Nodes (8): extract_frames(), get_video_duration(), _probe_hwaccels(), ffmpeg wrapper — pure Python, no Qt imports., Return hwaccel names that ffmpeg reports as available., Return video duration in seconds using ffprobe.      Raises:         Extracti, Extract one frame every interval_sec seconds using ffmpeg.      Args:, _require_binary()

### Community 13 - "Extractor Tests"
Cohesion: 0.22
Nodes (1): Tests for core/extractor.py

### Community 14 - "Pipeline Tests"
Cohesion: 0.46
Nodes (7): _make_config(), _make_frames(), Tests for core/pipeline.py, test_pipeline_download_error_captured(), test_pipeline_max_frames_limit(), test_pipeline_run_success(), test_pipeline_stop_event_cancels()

### Community 15 - "Prompt History"
Cohesion: 0.32
Nodes (6): append_entry(), _ensure_dir(), load_history(), Prompt history — persists prompt generation history as JSON., Load prompt history entries., Append a single history entry (capped at _MAX_ENTRIES).

### Community 16 - "Package Init"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **14 isolated node(s):** `Data models for ai-shot-cutter (immutable dataclasses, no Qt).`, `Tests for core/downloader.py`, `Tests for core/extractor.py`, `Tests for core/pipeline.py`, `Tests for core/vision.py` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FrameResult` connect `Video Downloader` to `Models & Tool Tests`, `Log Panel UI`, `Frame Card UI`, `Tools Panel`, `Prompt Panel`?**
  _High betweenness centrality (0.407) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `Log Panel UI` to `Video Downloader`, `Frame Card UI`, `App Entry & Settings`, `Tools Panel`, `Settings Panel UI`, `Prompt Panel`, `Input Panel`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Why does `AppSettings` connect `App Entry & Settings` to `Input Panel`, `Video Downloader`, `Log Panel UI`, `Settings Panel UI`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Are the 91 inferred relationships involving `FrameResult` (e.g. with `Pipeline` and `Pipeline orchestrator — pure Python, no Qt imports.  Flow:   1. Create output`) actually correct?**
  _`FrameResult` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `ExtractionError` (e.g. with `ffmpeg wrapper — pure Python, no Qt imports.` and `Return hwaccel names that ffmpeg reports as available.`) actually correct?**
  _`ExtractionError` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AppSettings` (e.g. with `Entry point for YouTube AI Frame Prompt Generator.` and `Smoke test: verify app window launches without crashing.`) actually correct?**
  _`AppSettings` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `MainWindow` (e.g. with `Entry point for YouTube AI Frame Prompt Generator.` and `Smoke test: verify app window launches without crashing.`) actually correct?**
  _`MainWindow` has 18 INFERRED edges - model-reasoned connections that need verification._