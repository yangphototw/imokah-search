@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=C:\Python314\python.exe"
set "LOG=logs\full-transcript-review.out.log"
set "ERR=logs\full-transcript-review.err.log"

rem One model at a time keeps RTX 3070 memory bounded and each clip is saved
rem immediately.  Re-running this file resumes only missing model results.
for %%M in (small medium large-v3) do (
    echo [%date% %time%] Starting %%M review pass>> "%LOG%"
    "%PYTHON%" review_audio_paragraphs.py --limit 5000 --models %%M >> "%LOG%" 2>> "%ERR%"
    if errorlevel 1 goto :failed
)

"%PYTHON%" evaluate_transcript_reviews.py --write >> "%LOG%" 2>> "%ERR%"
if errorlevel 1 goto :failed
"%PYTHON%" build_transcript_correction_ledger.py --write >> "%LOG%" 2>> "%ERR%"
if errorlevel 1 goto :failed
"%PYTHON%" quality_baseline.py --write >> "%LOG%" 2>> "%ERR%"
if errorlevel 1 goto :failed

echo [%date% %time%] Full transcript review completed>> "%LOG%"
exit /b 0

:failed
echo [%date% %time%] Full transcript review stopped; rerun this file to resume.>> "%ERR%"
exit /b 1
