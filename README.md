# 📷《我都OK啊》全頻道 AI 知識庫與 RAG 時間軸搜尋引擎

本專案為 YouTube 熱門攝影頻道 **《我都OK啊》(@imokahhhh - 道慈老師)** 的全量 1,038 部影片對白、主題精華與時間軸 RAG (Retrieval-Augmented Generation) 語意搜尋系統。

---

## ✨ 核心特色

1. **🎯 可追溯的部分匹配**：
   - 多詞查詢會保留有用的部分結果，但每張卡片只會列出實際符合的搜尋詞。例如搜尋 `GRIII 接拍` 時，只談街拍的影片會明確標示「標題符合『接拍』」，不會冒充為完整命中。
2. **🧠 段落級交集排序**：
   - `人像 光圈`、`GR3 街拍` 等複合查詢，會優先顯示在同一個可閱讀逐字稿段落中同時成立的結果；部分命中則標示其實際符合的詞。
3. **⚡ 靜態分片搜尋**：
   - 瀏覽器只下載與查詢詞相關的 gzip 分片；索引直接由公開段落建立，不依賴可能過期的 RAG offset。
4. **📝 可追溯的段落內容**：
   - 搜尋卡片顯示完整逐字稿段落、時間點與關鍵字醒目標示；未經人工核可的模型摘要不會被當作影片內容發布。
5. **🛡️ 部署前驗證**：
   - 索引會記錄段落來源雜湊；若逐字稿段落更新卻沒有重建搜尋索引，驗證會直接失敗。

---

## 🚀 快速開始 (Quick Start)

### 方式 A：Docker 一鍵啟動 (推薦)

```bash
# 建立並啟動容器
docker compose up -d --build

# 瀏覽網頁介面
http://localhost:8080
```

### 方式 B：Python 本地直接運行

```bash
# 啟動 Web 伺服器
python web_server.py
```

開啟瀏覽器造訪 `http://localhost:8080` 即可開始體驗！

### 靜態部署（Vercel 免費方案）

正式部署不會執行 Python 搜尋 API。更新逐字稿後，先建立公開段落，再由它建立靜態搜尋索引：

```bash
python build_public_paragraph_index.py
python build_static_search_index.py
python verify_static_site.py
python verify_search_relevance.py
```

此流程會將搜尋索引拆成 512 個 gzip 分片。搜尋分片與畫面顯示共用
`public/paragraph-index/` 這個段落來源，因此不會再因舊索引的位移失準而連到不相關對白。
瀏覽器只會下載與查詢關鍵字相符的分片；Vercel 因此只需提供 CDN 靜態檔案，沒有
Serverless 記憶體、冷啟動或函式逾時問題。

### 增量更新與自動排程

新影片的下載、Whisper 轉錄與索引更新都在本機執行；Vercel 只接收通過驗證的
`public/` 靜態檔案。先以唯讀方式檢查待處理影片：

```bash
python channel_update.py --dry-run
```

手動執行完整增量更新並推送：

```bash
auto_update.bat
```

安裝每天凌晨四點的 Windows 工作排程：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_update_schedule.ps1 -Time 04:00
```

排程可在電腦睡眠時喚醒執行；若電腦關機而錯過時間，會在下次登入後補跑。每次執行
都會將日誌寫入本機 `logs/`，而 `data/update_state.json` 保留可重試的處理狀態。

---

## 📂 專案架構說明

```
.
├── ai_oka.py                  # RAG 搜尋引擎核心 (分層召回 + 標題加補 + 詞頻 Boost)
├── batch_rag_indexer.py       # 倒排索引 Hash 檢索快取器
├── build_vector_db.py         # TF-IDF C-Accelerated 向量資料庫引擎
├── web_server.py              # HTTP RESTful API Web 伺服器 (Port: 8080)
├── fetch_youtube_stats.py     # 全頻道影片真實流量抓取器
├── Dockerfile                 # Docker 容器化構建檔
├── docker-compose.yml         # Docker Compose 一鍵部署配置
├── data/
│   ├── oka_knowledge_encyclopedia.json # 5 大維度全頻道知識大百科
│   ├── oka_youtube_map.json            # 1,038 部影片標準正宗繁中 Title 映射庫
│   ├── oka_rag_index.json              # 130 萬個 Whisper 秒數切片 RAG 索引
│   └── oka_video_stats.json            # 全頻道影片真實流量數據庫
└── web/
    ├── index.html             # 現代深色玻璃擬態 UI 介面
    ├── style.css              # 響應式 CSS3 樣式與動畫
    └── app.js                 # 前端 API 互動與 Loading 鎖保護
```

---

## 📜 授權與貢獻

本專案供《我都OK啊》頻道社群粉絲交流與學習使用。歡迎提交 Pull Requests 共同維護！
