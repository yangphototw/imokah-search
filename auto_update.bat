@echo off
echo ==================================================
echo   OKAH Project - Auto Update Script
echo ==================================================
set "NVIDIA_SITE_PACKAGES=%APPDATA%\Python\Python314\site-packages\nvidia"
set "PATH=%NVIDIA_SITE_PACKAGES%\cublas\bin;%NVIDIA_SITE_PACKAGES%\cudnn\bin;%NVIDIA_SITE_PACKAGES%\cuda_nvrtc\bin;%PATH%"
echo.
echo [1/5] Downloading latest videos and running Whisper...
python fetch_oka_knowledge.py

echo.
echo [2/5] Rebuilding fast inverted index...
python build_inverted_index.py

echo.
echo [3/5] Building Vercel static search shards...
python build_static_search_index.py

echo.
echo [4/5] Compressing large files for GitHub LFS...
python compress_data_for_github.py

echo.
echo [5/5] Pushing to GitHub...
git add .
git commit -m "auto: fetch new videos and rebuild static search index"
git push origin master

echo.
echo ==================================================
echo   Update completed!
echo ==================================================
