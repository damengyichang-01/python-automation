@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo.
echo  ============================================
echo    Build EXE for Office Automation Tools
echo  ============================================
echo.

echo  [1/4] Checking PyInstaller ...
python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo        not installed, installing now ...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo  [ERROR] pip install pyinstaller failed.
        pause
        exit /b 1
    )
)

echo  [2/4] Cleaning old output ...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo  [3/4] Building, this takes 1-3 minutes ...
python -m PyInstaller --noconfirm --clean --onefile --console ^
    --name office-tools ^
    --hidden-import openpyxl ^
    --hidden-import pandas ^
    menu.py
if errorlevel 1 (
    echo  [ERROR] Build failed. See messages above.
    pause
    exit /b 1
)

echo  [4/4] Renaming to Chinese name ...
if exist "dist\office-tools.exe" (
    move /y "dist\office-tools.exe" "dist\办公自动化工具包.exe" >nul
)

echo.
echo  Done. Output file:
echo    dist\办公自动化工具包.exe
echo.
echo  Copy that single .exe to any Windows PC and double click it.
echo  Python is NOT required on the target machine.
echo.
pause
