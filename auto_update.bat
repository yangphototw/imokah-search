@echo off
echo ==================================================
echo   OKAH Project - Auto Update Script
echo ==================================================
set "NVIDIA_SITE_PACKAGES=%APPDATA%\Python\Python314\site-packages\nvidia"
set "PATH=%NVIDIA_SITE_PACKAGES%\cublas\bin;%NVIDIA_SITE_PACKAGES%\cudnn\bin;%NVIDIA_SITE_PACKAGES%\cuda_nvrtc\bin;%PATH%"
echo.
echo [1/5] Discovering and processing new videos only...
python channel_update.py
if errorlevel 1 goto :error

echo.
echo [2/5] Verifying static deployment assets...
python verify_static_site.py
if errorlevel 1 goto :error

echo.
echo [3/5] Pushing to GitHub...
REM Only publish the static deploy output. Do not accidentally commit cookies,
REM audio, raw transcripts, or local databases with `git add .`.
git add public/catalog.json public/search-index
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
