@echo off
chcp 65001 > nul
title 🎤 Audio Transcriber
cls
echo.
echo ==========================================
echo        🎤 AUDIO TRANSCRIBER
echo ==========================================
echo.
echo Starting transcriber...
echo.
echo Controls:
echo   Ctrl + Alt + Space  -  Start/Stop recording
echo   Ctrl + C            -  Exit
echo.
echo ==========================================
echo.

python transcriber-req-win.py

echo.
echo Program finished. Press any key to close...
pause > nul
