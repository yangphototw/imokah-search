# 關鍵字審閱規範

使用者先要求 200 個攝影學習關鍵字，再審查「出現的是否真的該出現」。此輪只建立基線與問題，不改搜尋／摘要／逐字稿／知識地圖。

## 材料與範圍

- `keywords.json`：固定的 200 詞；`intent_groups` 是另一套找候選的提示，不是標準答案或全部合法同義詞。
- `baseline-results.jsonl`：200 詞的全部搜尋結果、全庫另外找的候選與時間点。
- `review-xxx-yyy.json`：每詞前三部、最多兩部缺少意圖字詞的結果，以及兩部未顯示但有段落的候選。這是明確有限的語意抽查，不能聲稱 6,383 個影片／查詢配對都已閱讀通過。
- 保留所有 200 詞，包括原庫可能沒有內容的詞；不要只挑成功題。
- 只讀指定包，按 10 詞一批；用原文段落 ID 到 `public/paragraph-index/*.json.gz` 回查。以既有摘要判斷影片重心，以原段落確認實際內容。需要更多結果才讀基線對應行，不把全庫塞入 Context。

## 判斷

觀眾想學關鍵字所指主題。涵蓋教學、操作、拍攝案例或有內容的器材評測。明確不適用、不同意某方法、比較另一種做法，也可能是有用內容；不能因是否定句就排除。

網站只收到關鍵字，沒有收到本清單的分類意圖。若另一詞義也是合理攝影需求（曲線可指構圖／後製；降噪可指影像／收音；遮光罩可指鏡頭／燈具），在 judgment 加 `intent_ambiguity: true`，理由說明條件；彙整時另列「不同意圖」，不算無條件錯片。明確的 ASR 亂字、型號混淆或較窄的查詢被擴成另一主題則不屬這種情況。

- `useful`：有可用解說／判斷／例子，值得在該詞出現。
- `mention`：只是列舉、順带一提或器材清單，來源真實但不適合前排推薦。
- `irrelevant`：不同詞義、過度擴張同義詞、錯型號，或無關內容。
- `unclear`：截段、語音辨識、題名單獨命中等無法核實；不要猜。

未顯示候選：`should_include`／`mention`／`irrelevant`／`unclear`。只有看過實際原段落、確認對學習主題有用，才可判 `should_include`。候選已確認不同詞義（例如 PS 遊戲機不是 Photoshop）使用 `irrelevant`，屬候選基準的假陽性，不是現有搜尋漏片。`irrelevant` 或批評排名時也須讀回原文；只見題名／摘要不能成立。段落證明有提及，但不代表整片都教該主題；一支長直播有可用段落也可以是好結果。

## 交付格式

各組獨立寫 `semantic-a.json`、`semantic-b.json`、`semantic-c.json`，不要改其他組檔案。

```json
{
  "reviewer": "a",
  "queries": [
    {
      "number": 1,
      "query": "曝光",
      "returned": [
        {"id": "videoID", "rank": 1, "verdict": "useful", "reason": "具體理由", "paragraph_ids": ["videoID:0"], "full_source_read": true}
      ],
      "missing": [
        {"id": "videoID", "verdict": "should_include", "reason": "具體理由", "paragraph_ids": ["videoID:0"], "full_source_read": true}
      ],
      "conclusion": "front_relevant|ranking_issue|recall_issue|mixed_issue|no_evidence|needs_review",
      "note": "簡短發現；無需每題寫長摘要"
    }
  ]
}
```

每詞交付實際包內所有 returned_to_review 與 missing_to_review 的判斷；不要把未看的其他結果寫成通過。excerpt 足以支持明確正相關時可標 full_source_read=false，模糊處回讀完整段落及必要相鄰段落。對 `should_include`／`irrelevant` 必須 full_source_read=true。若語意基準本身太寬或錯誤，要在 note 指出，不順從程式標籤。

來源工具可以用 Python (`C:/Python314/python.exe -X utf8`) 解壓分片；第一次讀可建立 ID 到段落的本機暫存，只存本次審查目錄下，不改正式資料。避免重讀大包。最後對主 Agent 只回範圍、最重要 3–5 個發現、檔案位置、未完成之處。
