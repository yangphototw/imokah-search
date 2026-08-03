@echo off
chcp 65001 > nul
echo ==================================================
echo   《我都ok啊》專案 - 一鍵全自動更新腳本
echo ==================================================
echo.
echo [1/5] 正在掃描並下載最新影片音訊、執行 Whisper 語音辨識...
python fetch_oka_knowledge.py

echo.
echo [2/5] 正在重建秒級倒排搜尋索引...
python build_inverted_index.py

echo.
echo [3/5] 正在打包 100%% 純靜態 Vercel 分片資料庫...
python build_static_search_index.py

echo.
echo [4/5] 正在壓縮大型檔案，準備推送至 GitHub...
python compress_data_for_github.py

echo.
echo [5/5] 正在推送到 GitHub 並觸發 Vercel 部署...
git add .
git commit -m "auto: fetch new videos and rebuild static search index"
git push origin master

echo.
echo ==================================================
echo   更新大功告成！Vercel 將在數秒內自動完成新版部署。
echo ==================================================
pause
