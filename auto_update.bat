@echo off
echo ==================================================
echo   OKAH Project - Auto Update Script
echo ==================================================
set "NVIDIA_SITE_PACKAGES=%APPDATA%\Python\Python314\site-packages\nvidia"
set "PATH=%NVIDIA_SITE_PACKAGES%\cublas\bin;%NVIDIA_SITE_PACKAGES%\cudnn\bin;%NVIDIA_SITE_PACKAGES%\cuda_nvrtc\bin;%PATH%"
echo.
echo [1/9] Discovering and processing new videos only...
python channel_update.py
if errorlevel 1 goto :error

echo.
echo [2/9] Applying the public text quality gate...
python content_quality.py --rewrite-catalog
if errorlevel 1 goto :error

echo.
echo [3/9] Rewriting public video copy...
python rewrite_public_copy.py
if errorlevel 1 goto :error

echo.
echo [4/9] Updating the hash-based processing manifest...
python build_processing_manifest.py
if errorlevel 1 goto :error

echo.
echo [5/9] Building the Markdown knowledge base...
python build_markdown_knowledge_base.py
if errorlevel 1 goto :error

echo.
echo [6/9] Verifying static deployment assets...
python verify_static_site.py
if errorlevel 1 goto :error

echo.
echo [7/9] Verifying the Markdown knowledge base...
python verify_markdown_knowledge_base.py
if errorlevel 1 goto :error

echo.
echo [8/9] Pushing to GitHub...
REM Only publish the static deploy output. Do not accidentally commit cookies,
REM audio, raw transcripts, or local databases with `git add .`.
git add public/catalog.json public/search-index public/paragraph-index data/oka_video_summaries.json data/oka_youtube_map.json data/processing_manifest.json knowledge
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "auto: refresh static search index"
    git push origin master
) else (
    echo No deployable static changes to push.
)

echo.
echo ==================================================
echo   Update completed!
echo ==================================================
goto :eof

:error
echo Update stopped because a verification step failed.
exit /b 1
