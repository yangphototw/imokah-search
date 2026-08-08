@echo off
echo ==================================================
echo   OKAH Project - Auto Update Script
echo ==================================================
set "NVIDIA_SITE_PACKAGES=%APPDATA%\Python\Python314\site-packages\nvidia"
set "PATH=%NVIDIA_SITE_PACKAGES%\cublas\bin;%NVIDIA_SITE_PACKAGES%\cudnn\bin;%NVIDIA_SITE_PACKAGES%\cuda_nvrtc\bin;%PATH%"
echo.
echo [1/7] Discovering and processing new videos only...
python channel_update.py
if errorlevel 1 goto :error

echo.
echo [2/7] Applying the public text quality gate...
python content_quality.py --rewrite-catalog
if errorlevel 1 goto :error

echo.
echo [3/7] Rewriting public video copy...
python rewrite_public_copy.py
if errorlevel 1 goto :error

echo.
echo [4/7] Verifying static deployment assets...
python verify_static_site.py
if errorlevel 1 goto :error

echo.
echo [5/7] Pushing to GitHub...
REM Only publish the static deploy output. Do not accidentally commit cookies,
REM audio, raw transcripts, or local databases with `git add .`.
git add public/catalog.json public/search-index public/paragraph-index data/oka_video_summaries.json data/oka_youtube_map.json
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
