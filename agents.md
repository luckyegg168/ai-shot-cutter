# YouTube AI Frame Prompt Generator — Agent Orchestration Plan

## Agent Assignments

### Phase 0: Scaffold
**Agent:** `general-purpose`
- Create directory structure
- Generate `requirements.txt`, `pyproject.toml`
- Verify imports compile

---

### Phase 1: Core Business Logic
**Agent:** `tdd-guide`
- Write unit tests first for each module in `core/`
- Implement `models.py`, `downloader.py`, `extractor.py`, `vision.py`, `pipeline.py`
- Mock yt-dlp subprocess, ffmpeg subprocess, openai client
- Target: ≥80% coverage on `core/`

**Parallel sub-tasks (launch simultaneously):**
- Agent A → `downloader.py` + `test_downloader.py`
- Agent B → `extractor.py` + `test_extractor.py`
- Agent C → `vision.py` + `test_vision.py`

Then sequentially:
- Agent D → `pipeline.py` + `test_pipeline.py` (depends on A, B, C)

---

### Phase 2: Worker Thread
**Agent:** `tdd-guide`
- Write `workers/pipeline_worker.py`
- Test signal emissions with `pytest-qt`
- Verify cancellation via `stop_event`

---

### Phase 3: GUI Widgets
**Agent:** `general-purpose` (PySide6 specialist)

**Parallel builds:**
- Agent A → `ui/input_panel.py` (form + validation)
- Agent B → `ui/gallery_widget.py` + `ui/frame_card.py`
- Agent C → `ui/prompt_panel.py` + `ui/log_panel.py`

Then sequentially:
- Agent D → `ui/main_window.py` (assembles all panels)

---

### Phase 4: Output & Settings
**Agent:** `general-purpose`
- `utils/file_utils.py` — output folder, JSON writer, summary.md generator
- `utils/settings.py` — QSettings wrapper
- `utils/i18n.py` — translations loader (see i18n section)

---

### Phase 5: Code Review
**Agent:** `code-reviewer`
- Review all `core/` modules
- Review all `ui/` modules
- Focus: no Qt calls in core, proper signal/slot patterns, error propagation

---

### Phase 6: Security Review
**Agent:** `security-reviewer`
- API key storage (QSettings — not plaintext in code)
- No hardcoded credentials
- Subprocess injection prevention (ffmpeg/yt-dlp args sanitized)
- Output path traversal prevention

---

### Phase 7: E2E / Smoke Tests
**Agent:** `e2e-runner` (using `pytest-qt`)
- Launch app
- Fill form with test URL (short public domain video)
- Verify gallery populates
- Verify output folder created
- Verify Cancel stops job

---

## Agent Communication Protocol

All agents write to the same repo. Handoff order:

```
tdd-guide (core) 
  → general-purpose (workers)
  → general-purpose (ui widgets, parallel)
  → general-purpose (main_window assembly)
  → general-purpose (utils/output)
  → code-reviewer
  → security-reviewer
  → e2e-runner
```

Each agent reads `spec.md` for contracts and `plan.md` for phase context.

---

## Implementation Agent Prompt Template

When launching any implementation agent, include:

```
Context: Building "YouTube AI Frame Prompt Generator" — PySide6 desktop app.
Spec: D:/ai-shot-cutter/spec.md
Plan: D:/ai-shot-cutter/plan.md

Your task: [SPECIFIC PHASE]

Rules:
- No Qt imports in core/ modules
- All subprocess calls must sanitize arguments (no shell=True with user input)
- API key never logged or printed
- Follow TDD: tests first, then implementation
- 80%+ coverage required for core/
- Use immutable dataclasses (frozen=True where possible)
- i18n: all user-visible strings via tr() — see i18n spec section
```

---

## i18n Agent Task

**Agent:** `general-purpose`

### Goal
Add multilingual support with `zh-TW` as default language.

### Implementation approach
Use Qt's built-in `QTranslator` + `.ts`/`.qm` files via `Qt Linguist`.

### File structure
```
i18n/
  app_zh_TW.ts     # Traditional Chinese (default)
  app_en_US.ts     # English
  app_ja_JP.ts     # Japanese (optional v1.1)
  app_zh_TW.qm     # Compiled binary
  app_en_US.qm
```

### `utils/i18n.py`
```python
from PySide6.QtCore import QTranslator, QLocale, QCoreApplication

def load_translator(app: QCoreApplication, lang: str = "zh_TW") -> QTranslator:
    translator = QTranslator()
    qm_path = Path(__file__).parent.parent / "i18n" / f"app_{lang}.qm"
    if qm_path.exists():
        translator.load(str(qm_path))
        app.installTranslator(translator)
    return translator
```

### Language selection
- `utils/settings.py` stores `language` key, default `"zh_TW"`
- `InputPanel` → Settings dialog (gear icon) → Language `QComboBox`
- Language change triggers `QMessageBox` "Restart to apply"

### String wrapping rule
Every user-visible string in UI code must use:
```python
self.tr("English source string")
# or at module level:
QCoreApplication.translate("ClassName", "English source string")
```

Never use bare string literals in UI labels.

### zh-TW translation table (initial)

| English | 繁體中文 |
|---------|---------|
| YouTube URL | YouTube 網址 |
| Interval (sec) | 擷取間隔（秒） |
| OpenAI API Key | OpenAI API 金鑰 |
| Prompt Type | Prompt 類型 |
| Image Prompt | 圖像 Prompt |
| Video Prompt | 影片 Prompt |
| Max Frames (0=unlimited) | 最大影格數（0=不限） |
| Start | 開始 |
| Stop | 停止 |
| Open Output | 開啟輸出資料夾 |
| Copy Prompt | 複製 Prompt |
| Regenerate | 重新生成 |
| Clear Log | 清除日誌 |
| Settings | 設定 |
| About | 關於 |
| Frame %1 / %2 | 影格 %1 / %2 |
| Downloading... | 下載中... |
| Extracting frames... | 擷取影格中... |
| Analyzing frame %1 of %2 | 分析第 %1 / %2 張影格 |
| Job cancelled | 工作已取消 |
| Job completed | 工作完成 |
| Error: %1 | 錯誤：%1 |
| Invalid URL | 無效的網址 |
| API key required | 需要 API 金鑰 |
| ffmpeg not found | 找不到 ffmpeg |
| Language | 語言 |
| Restart to apply | 重新啟動後生效 |
| Dark Theme | 深色主題 |
| Light Theme | 淺色主題 |

### Build command
```bash
# Extract strings → update .ts files
pyside6-lupdate ui/*.py utils/*.py -ts i18n/app_zh_TW.ts i18n/app_en_US.ts

# Compile .ts → .qm
pyside6-lrelease i18n/app_zh_TW.ts -qm i18n/app_zh_TW.qm
pyside6-lrelease i18n/app_en_US.ts -qm i18n/app_en_US.qm
```

Add both commands to a `scripts/build_i18n.py` helper.

### Acceptance criteria
- App launches in zh-TW by default on any OS locale
- All labels, buttons, dialogs show Traditional Chinese
- Switching to en_US and restarting shows English
- No bare string literals in UI code (`rg '"[A-Z]' ui/` returns 0 matches)

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
