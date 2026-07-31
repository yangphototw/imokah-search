# 🎬 《我都ok啊》專案接續與交接說明文件 (OKA Project Handover Document)

> **建立時間**：2026-07-29
> **專案資料夾**：`D:\Gemini_CLI\260726_AIOK`
> **專屬音訊歸檔目錄**：`F:\AI_Youtube\MP3\Oka_*`

---

## 📌 一、 專案背景與目標
本專案為 YouTube 頻道 **《我都ok啊》(@imokahhhh)** 的專屬 AI 知識庫與專家問答系統。頻道內容涵蓋：**攝影器材評測（Nikon Zf, Ricoh GR III, Sony a7IV 等）、攝影心法與觀念、攝影讀書會大師導讀、海外/國內旅遊自駕 Vlog、以及創作者生活隨筆與直播**。

---

## 🏆 二、 過去幾天完成的核心成果 (Completed Work)

### 1. 📥 【階段一：全頻道 1,038 部音訊檔 100% 下載與歸檔】
- **完成度**：**`1038 / 1038 部 (100.0%)`** 🏆
- **實體檔案**：已全數無損快取並移動歸檔至 `F:\AI_Youtube\MP3\Oka_[video_id].webm / .m4a / .mp3`（總計 34.28 GB）。
- **技術突破**：整合 Node.js EJS Challenge Solver 與 YouTube Cookie，下載速率達 38.96 MiB/s。

### 2. ⚡ 【階段二：語音轉文字檔 (Whisper STT) 100% 完工】
- **完成度**：**`1038 / 1038 部 (100.0%)`** 🏆
- **實體檔案**：儲存在 `D:\Gemini_CLI\260726_AIOK\data\transcripts\`
  - `{video_id}_transcript.json`：供程式微觀與時間對齊使用。
  - `{video_id}_transcript.md`：供人類閱讀，每一句都含有可點擊直跳 YouTube 對應秒數的網址。
- **技術突破**：使用 `faster-whisper` + RTX 3070 CUDA GPU `float16` 硬體加速，且強制限制 `cpu_threads=2`，使 CPU 保持在 15~25% 低溫輕負載。

### 3. 📚 【階段三：時間戳記 RAG 索引庫 100% 完工】
- **索引檔案**：`D:\Gemini_CLI\260726_AIOK\data\oka_rag_index.json`
- **對話切片數**：收錄全頻道共 **1,307,252 個帶有秒級直跳網址的時間點對話切片**。

---

## 🎯 三、 新 Session 的接續目標 (Next Goals)

請在新開的 Session（於 `D:\Gemini_CLI\260726_AIOK` 目錄）中執行以下升級計畫：

### 🎯 目標一：建置全頻道主題分類大百科與知識樹
- **描述**：撰寫腳本掃描 1,038 部影片逐字稿，自動歸納分類為 5 大主題維度：
  1. 📷 **攝影器材與鏡頭評測**
  2. 🎨 **攝影心法與觀念實戰**
  3. 📚 **攝影讀書會與大師導讀**
  4. ✈️ **國內外攝影旅行與自駕攻略**
  5. 💬 **創作者生活隨筆與直播 Q&A**
- **產出目標**：
  - `data/oka_knowledge_encyclopedia.json`
  - `data/oka_knowledge_tree.md`

### 🎯 目標二：建置本地 100% 免費 Vector 語意向量庫
- **描述**：使用本地輕量向量模型（如 ChromaDB / FastEmbed / BAAI-bge），將 1,307,252 個切片建立語意索引，存入 `data/oka_vector_db/`。
- **效果**：使使用者詢問抽象概念（如「對街拍尷尬的看法」）時能達 99% 抽象語意精準比對。

### 🎯 目標三：優化 CLI 專家互動引擎
- **檔案**：`ai_oka.py` 與 `main.py`
- **效果**：打造專屬「《我都ok啊》攝影與生活 AI 專家」，支援自然對話、關鍵字檢索與秒級播放連結輸出。

---

## 🛠️ 四、 常用腳本與指令參考
- 查詢進度：`python get_pipeline_progress.py`（位於 `D:\Gemini_CLI\260726_AIGooaye`）
- 檢索 CPL/偏光對話：`python search_cpl.py`（位於 `D:\Gemini_CLI\260726_AIOK`）
- 測試單影片轉譯：`python transcribe_episodes.py [video_id]`
