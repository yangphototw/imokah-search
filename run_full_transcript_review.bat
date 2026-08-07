@echo off
setlocal
cd /d "%~dp0"
C:\Python314\python.exe review_audio_paragraphs.py --limit 4657 --models small,medium,large-v3 >> logs\full-transcript-review.out.log 2>> logs\full-transcript-review.err.log
