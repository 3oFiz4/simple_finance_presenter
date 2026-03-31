@echo off
setlocal
title Money Tracker

set "SCRIPT=%~dp0money_graph.py"

where python >nul 2>&1 || (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

python -c "import rich" >nul 2>&1 || (
    echo Installing rich library...
    pip install rich
)

if "%~1"=="" (
    echo.
    echo   Drag a .txt file onto this batch, or enter path:
    echo.
    set /p "F=   File: "
    python "%SCRIPT%" "%F%"
) else (
    python "%SCRIPT%" "%~1"
)

echo.
pause
