@echo off
cd /d "%~dp0"
title AI-Powered Mine Rescue Station - SIH PS 26039
echo =======================================================
echo Launching AI Mine Rescue Station (YOLOv8 + Telemetry)...
echo =======================================================
"C:\Users\sanja\AppData\Local\Programs\Python\Python311\python.exe" "rescue_station.py"
if %errorlevel% neq 0 (
    echo.
    echo Application exited with code %errorlevel%.
    pause
)
