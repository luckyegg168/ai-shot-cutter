# YouTube AI Frame Prompt Generator

一款 **PySide6** 桌面應用程式，自動下載 YouTube 影片、擷取關鍵影格，並透過 **GPT-4o Vision** 為每一張影格生成 AI 圖像/影片 Prompt。

---

## 功能特色

| 功能 | 說明 |
|------|------|
| 自動下載 | 貼上 YouTube 網址即可下載（支援 1080p） |
| 智慧擷取 | 可自訂擷取間隔（秒），最多 N 張影格 |
| GPT-4o 分析 | 自動為每張影格生成描述性 Prompt |
| 雙模式 | 支援「圖像 Prompt」與「影片 Prompt」兩種輸出風格 |
| 即時預覽 | 縮圖畫廊 + 大圖預覽 + 一鍵複製 Prompt |
| 結果匯出 | 自動儲存 `results.json` + `summary.md` |
| 深色主題 | Catppuccin 風格深色介面 |

---

## 系統需求

- Python **3.11+**
- **ffmpeg** & **ffprobe**（需在 PATH 中）
- OpenAI API Key（`sk-...`）

---

## 安裝步驟

### 1. 安裝 ffmpeg

**Windows（Chocolatey）**
```powershell
choco install ffmpeg
```

**Windows（手動）**
1. 從 https://ffmpeg.org/download.html 下載
2. 解壓縮後將 `bin/` 加入系統 PATH

**macOS**
```bash
brew install ffmpeg
```

**Ubuntu / Debian**
```bash
sudo apt install ffmpeg
```

### 2. 建立 Python 虛擬環境

```bash
cd ai-shot-cutter
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

---

## 執行應用程式

```bash
python main.py
```

或透過 pyproject.toml 安裝後執行：

```bash
pip install -e .
ai-shot-cutter
```

---

## 使用說明

### 步驟一：填寫設定

| 欄位 | 說明 |
|------|------|
| **YouTube URL** | 貼上完整的 YouTube 影片網址 |
| **擷取間隔（秒）** | 每隔幾秒截取一張影格，預設 5 秒 |
| **OpenAI API Key** | 以 `sk-` 開頭的 OpenAI API 金鑰 |
| **Prompt 類型** | `image` = 靜態圖像 Prompt；`video` = 動態影片 Prompt |
| **最大影格數** | 0 = 不限；輸入正整數則最多分析 N 張 |
| **輸出資料夾** | 輸出根目錄，預設 `~/ai-shot-cutter/output` |

### 步驟二：開始分析

按下 **開始** 按鈕，程式會依序：
1. 下載影片到暫存目錄
2. 用 ffmpeg 擷取影格（JPG）
3. 呼叫 GPT-4o Vision 分析每張影格
4. 在畫廊顯示縮圖

### 步驟三：查看結果

- 點擊縮圖 → 右側面板顯示大圖與 Prompt
- **複製 Prompt** 按鈕 → 複製到剪貼簿
- **重新生成** 按鈕 → 重新呼叫 GPT-4o 分析同一張影格
- **File > Open Output** → 開啟輸出資料夾

### 步驟四：取得輸出檔案

每次執行後，輸出目錄結構如下：

```
output/
└── <video_id>_YYYYMMDD_HHMMSS/
    ├── frames/
    │   ├── frame_0001.jpg
    │   ├── frame_0002.jpg
    │   └── ...
    ├── results.json       ← 完整 JSON 結果
    └── summary.md         ← Markdown 摘要表格
```

#### results.json 欄位說明

```json
{
  "schema_version": "1.0",
  "url": "https://youtube.com/...",
  "prompt_type": "image",
  "created_at": "2024-01-15T12:00:00",
  "frames": [
    {
      "index": 1,
      "timestamp_sec": 5.0,
      "image_path": "frames/frame_0001.jpg",
      "prompt": "Wide cinematic establishing shot..."
    }
  ]
}
```

---

## 執行測試

```bash
pip install -e ".[dev]"

# 全部測試
pytest tests/ -v

# 含覆蓋率報告
pytest tests/ --cov=core --cov-report=term-missing
```

---

## 環境變數（選用）

| 變數 | 說明 |
|------|------|
| `AI_SHOT_CUTTER_OUTPUT` | 覆蓋預設輸出目錄 |
| `OPENAI_API_KEY` | 若設定則自動帶入 API Key 欄位 |

---

## 常見問題

**Q: `ffmpeg not found on PATH` 錯誤**  
A: 確認 ffmpeg 已安裝並加入系統 PATH，重新開啟終端機後再試。

**Q: `401 Unauthorized` 錯誤**  
A: 請確認 API Key 正確，並確認該 Key 有 GPT-4o 存取權限。

**Q: 進度卡在下載階段**  
A: 可能是網路問題或 yt-dlp 版本過舊；執行 `pip install -U yt-dlp` 後再試。

**Q: 縮圖顯示灰色方塊**  
A: 影格圖檔可能尚未寫入磁碟；等待分析完成後再點擊。

---

## 授權

MIT License — 詳見 [LICENSE](LICENSE)
