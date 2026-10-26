@echo off
cd /d "%~dp0"
title M.I.N.E.R.S. V3 - Autonomous Map Navigation Station
echo =====================================================================
echo Launching M.I.N.E.R.S. Version-3 Autonomous Map Navigation GUI
echo SIH PS ID: 26039 | Govt. of Jharkhand
echo =====================================================================
echo Starting V3 Dashboard...
"C:\Users\sanja\AppData\Local\Programs\Python\Python311\python.exe" "rescue_station_v3.py"
if %errorlevel% neq 0 (
    echo.
    echo Application exited with code %errorlevel%. Press any key to close...
    pause >nul
)
