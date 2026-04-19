# 系統架構知識圖譜

## 模組依賴圖

```mermaid
graph TD
    subgraph Entry["▶ 入口點"]
        main["main.py\nQApplication"]
    end

    subgraph UI["🖥️ UI 層（ui/）"]
        MW["main_window.py\nMainWindow(QMainWindow)"]
        IP["input_panel.py\nInputPanel(QWidget)\n+ clipboard banner\n+ recent URLs combo"]
        GW["gallery_widget.py\nGalleryWidget(QScrollArea)\n+ sort combo\n+ starred filter\n+ empty state"]
        FC["frame_card.py\nFrameCard(QFrame)\n+ star/favorite button"]
        PP["prompt_panel.py\nPromptPanel(QWidget)\n+ char/word counter"]
        LP["log_panel.py\nLogPanel(QWidget)"]
        QSS["styles.qss\n深色主題\n+ QDoubleSpinBox\n+ star_btn\n+ toast_widget"]
        TOAST["toast.py\nToast(QLabel)\n自動淡出通知"]
    end

    subgraph Workers["⚙️ Worker 層（workers/）"]
        PW["pipeline_worker.py\nPipelineWorker(QThread)"]
    end

    subgraph Core["🔩 核心層（core/）"]
        PL["pipeline.py\nPipeline.run()"]
        DL["downloader.py\ndownload_video()"]
        EX["extractor.py\nextract_frames()"]
        VI["vision.py\nanalyze_frame()\n+ character/landscape\n+ product/architecture\n  prompt types"]
        MD["models.py\nJobConfig / FrameResult\nJobResult / Exceptions"]
    end

    subgraph Utils["🛠️ 工具層（utils/）"]
        FU["file_utils.py\ncreate_output_dir\nwrite_results_json\nwrite_summary_md"]
        ST["settings.py\nAppSettings(QSettings)\n+ get/add_recent_urls()\n+ get/set_always_on_top()"]
    end

    subgraph External["🌐 外部依賴"]
        YT["yt-dlp\nYouTube 下載"]
        FF["ffmpeg / ffprobe\n影格擷取"]
        OA["OpenAI GPT-4o\nVision API"]
    end

    %% Entry → UI
    main --> MW
    main --> ST

    %% UI 內部
    MW --> IP
    MW --> GW
    MW --> PP
    MW --> LP
    MW --> TOAST
    GW --> FC
    MW --> QSS

    %% UI → Worker
    IP -- "job_requested(JobConfig)" --> PW
    PW -- "progress_updated" --> LP
    PW -- "frame_ready(FrameResult)" --> GW
    PW -- "job_finished(JobResult)" --> MW
    PW -- "error_occurred(str)" --> LP

    %% Worker → Core
    PW --> PL

    %% Core 內部
    PL --> DL
    PL --> EX
    PL --> VI
    PL --> MD
    DL --> MD
    EX --> MD
    VI --> MD

    %% Core → Utils
    PL --> FU

    %% Utils → Settings
    IP --> ST
    ST --> ST

    %% Core → External
    DL --> YT
    EX --> FF
    VI --> OA

    style Entry fill:#1e1e2e,color:#cdd6f4
    style UI fill:#181825,color:#cdd6f4
    style Workers fill:#1e1e2e,color:#cdd6f4
    style Core fill:#181825,color:#cdd6f4
    style Utils fill:#1e1e2e,color:#cdd6f4
    style External fill:#11111b,color:#a6adc8
```

---

## 資料流程圖

```mermaid
sequenceDiagram
    participant User
    participant InputPanel
    participant PipelineWorker
    participant Pipeline
    participant Downloader
    participant Extractor
    participant Vision
    participant FileUtils
    participant GalleryWidget

    User->>InputPanel: 填寫表單 → 按「開始」
    InputPanel->>PipelineWorker: emit job_requested(JobConfig)
    PipelineWorker->>Pipeline: run(config, callbacks, stop_event)

    Pipeline->>FileUtils: create_output_dir()
    Pipeline->>Downloader: download_video(url)
    Downloader-->>Pipeline: Path(video.mp4)

    Pipeline->>Extractor: extract_frames(video, interval)
    Extractor-->>Pipeline: list[Path] (frames)

    loop 每張影格
        Pipeline->>Vision: analyze_frame(frame, api_key, type)
        Vision-->>Pipeline: prompt (str)
        Pipeline->>PipelineWorker: on_frame_done(FrameResult)
        PipelineWorker->>GalleryWidget: emit frame_ready(FrameResult)
    end

    Pipeline->>FileUtils: write_results_json()
    Pipeline->>FileUtils: write_summary_md()
    Pipeline-->>PipelineWorker: JobResult
    PipelineWorker->>InputPanel: emit job_finished(JobResult)
```

---

## 類別關係圖

```mermaid
classDiagram
    class JobConfig {
        +url: str
        +interval_sec: int
        +api_key: str
        +output_dir: Path
        +prompt_type: str
        +max_frames: int
    }

    class FrameResult {
        +index: int
        +timestamp_sec: float
        +image_path: Path
        +prompt: str
        +timestamp_label: str
    }

    class JobResult {
        +frames: list[FrameResult]
        +success: bool
        +error_message: str
    }

    class Pipeline {
        +run(config, on_progress, on_frame_done, stop_event) JobResult
    }

    class PipelineWorker {
        +progress_updated: Signal
        +frame_ready: Signal
        +job_finished: Signal
        +error_occurred: Signal
        +stop() None
        +run() None
    }

    class MainWindow {
        -_worker: PipelineWorker
        -_settings: AppSettings
        +_start_job(config)
        +_stop_job()
        +_on_regenerate(frame)
    }

    class AppSettings {
        +api_key: str
        +interval: int
        +prompt_type: str
        +output_dir: Path
        +max_frames: int
        +theme: str
    }

    JobResult "1" *-- "0..*" FrameResult
    Pipeline ..> JobConfig : uses
    Pipeline ..> JobResult : creates
    PipelineWorker --> Pipeline : runs
    MainWindow --> PipelineWorker : controls
    MainWindow --> AppSettings : reads/writes
```

---

## 目錄結構

```
ai-shot-cutter/
├── main.py                  ← 應用程式入口點
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── README.md
├── KNOWLEDGE_GRAPH.md       ← 本文件
│
├── core/                    ← 核心業務邏輯（無 Qt 依賴）
│   ├── __init__.py
│   ├── models.py            ← 資料模型與例外
│   ├── downloader.py        ← yt-dlp 包裝
│   ├── extractor.py         ← ffmpeg 包裝
│   ├── vision.py            ← GPT-4o Vision API
│   └── pipeline.py          ← 任務協調
│
├── workers/                 ← Qt 執行緒橋接
│   ├── __init__.py
│   └── pipeline_worker.py   ← QThread 包裝
│
├── ui/                      ← 介面元件
│   ├── __init__.py
│   ├── styles.qss           ← 深色主題樣式表（+ QDoubleSpinBox, star_btn, toast）
│   ├── input_panel.py       ← 表單輸入面板（+ clipboard banner, recent URLs）
│   ├── frame_card.py        ← 縮圖卡片（+ 星號收藏按鈕）
│   ├── gallery_widget.py    ← 3欄縮圖畫廊（+ sort, starred filter, empty state）
│   ├── prompt_panel.py      ← Prompt 預覽面板（+ 字元/字數計數器）
│   ├── log_panel.py         ← 進度列 + 日誌
│   ├── toast.py             ← Toast 通知 overlay（v1.3 新增）
│   └── main_window.py       ← 主視窗（+ clipboard detect, always-on-top, shortcuts help）
│
├── utils/                   ← 無狀態工具函式
│   ├── __init__.py
│   ├── file_utils.py        ← 輸出目錄 / JSON / MD
│   └── settings.py          ← QSettings 包裝（+ recent_urls, always_on_top）
│
├── tests/                   ← pytest 測試套件
│   ├── __init__.py
│   ├── test_downloader.py
│   ├── test_extractor.py
│   ├── test_vision.py
│   ├── test_pipeline.py
│   └── test_gui_smoke.py
│
├── assets/                  ← 靜態資源（圖示等）
└── output/                  ← 預設輸出根目錄（.gitignore）
```

---

## 變更歷史

| 版本 | 日期 | 內容 | 影響範圍 |
|------|------|------|----------|
| v1.0 | 2025-01-01 | 初始架構圖建立 | 全部 |
| v1.1 | 2025-01-01 | v1.1 修復與 5 個新功能 (F-01～F-05) | ui/, core/ |
| v1.2 | 2025-01-01 | v1.2 程式碼品質 + 10 個新功能 (F-06～F-15) | core/, ui/, utils/ |
| v1.3 | 2025-07-18 | v1.3 UI 整體優化 + 10 個新功能 (F-16～F-25) | ui/toast.py(新增), core/vision.py, utils/settings.py, ui/frame_card.py, ui/gallery_widget.py, ui/prompt_panel.py, ui/input_panel.py, ui/main_window.py, ui/styles.qss |
