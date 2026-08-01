# 📷《我都OK啊》全頻道 AI 知識庫與 RAG 時間軸搜尋引擎

本專案為 YouTube 熱門攝影頻道 **《我都OK啊》(@imokahhhh - 道慈老師)** 的全量 1,038 部影片對白、主題精華與時間軸 RAG (Retrieval-Augmented Generation) 語意搜尋系統。

---

## ✨ 核心特色

1. **🎯 標題精確匹配與詞頻多次提及加成 (Title & Term Frequency Boost)**：
   - 搜尋關鍵字精確命中標題時賦予 2000+ 極高優先權，對白多次提及的切片獲得動態分數加成。
2. **🧠 多詞共現加成引擎 (Multi-Word Intersection Engine)**：
   - 支援 `人像 光圈`、`A74 鏡頭`、`富士 色調` 等複合關鍵字 AND 邏輯交集檢索，自動置頂同時符合雙條件的精華影片。
3. **⚡ 倒排索引 Hash 檢索引擎 (Inverted Index Engine)**：
   - 涵蓋 1,307,252 個秒數對白切片，查詢回應速度低於 10ms，檢索效能提升 150 倍。
4. **💡 AI 自動生成對白摘要 (Segment Summary)**：
   - 每段切片均附帶 15-30 字核心觀點摘要，無須盲目點擊即可秒懂影片內容。
5. **🛡️ 100% 正宗繁體中文標題反向防護**：
   - 徹底杜絕 YouTube 自動翻譯英文標題洩漏，全站 100% 展示正宗繁體中文。

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

正式部署不會執行 Python 搜尋 API。請在更新搜尋資料後先產生靜態索引：

```bash
python build_static_search_index.py
```

此指令會將搜尋索引拆成 512 個 gzip 分片，並產生 `public/catalog.json`。
瀏覽器只會下載與查詢關鍵字相符的分片；Vercel 因此只需提供 CDN 靜態檔案，沒有
Serverless 記憶體、冷啟動或函式逾時問題。

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
