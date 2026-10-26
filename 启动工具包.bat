@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo  [ERROR] Python not found on this computer.
    echo.
    echo  Please install Python 3.8 or newer:
    echo      https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: during installation, tick
    echo      "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

python menu.py
if errorlevel 1 pause
