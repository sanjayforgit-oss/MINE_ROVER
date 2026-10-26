@echo off
cd /d "%~dp0"
title AI Mine Rescue Station V2 - SIH PS 26039
echo =====================================================================
echo Launching AI-Powered Underground Mine Rescue & Reconnaissance System V2
echo SIH PS ID: 26039 | Govt. of Jharkhand
echo =====================================================================
echo Starting GUI...
"C:\Users\sanja\AppData\Local\Programs\Python\Python311\python.exe" "rescue_station_v2.py"
if %errorlevel% neq 0 (
    echo.
    echo Application exited with code %errorlevel%. Press any key to close...
    pause >nul
)
