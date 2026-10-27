@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

REM  用法：
REM    build_exe.bat          -> 单文件版（默认，交付用）
REM    build_exe.bat fast     -> 文件夹版（启动快 10 倍，自己用）

set MODE=%1
if /I "%MODE%"=="fast" goto FAST

echo.
echo  ==========================================
echo    Build: ONE FILE  (单文件版, 约 31 MB)
echo  ==========================================
echo.

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo  Installing PyInstaller ...
    python -m pip install pyinstaller
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller --noconfirm --clean --onefile --console ^
    --name office-tools ^
    --hidden-import openpyxl ^
    --hidden-import pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module scipy ^
    --exclude-module tkinter ^
    --exclude-module IPython ^
    --exclude-module pytest ^
    menu.py
if errorlevel 1 goto FAIL

if exist "dist\office-tools.exe" move /y "dist\office-tools.exe" "dist\办公自动化工具包.exe" >nul

echo.
echo  Done:  dist\办公自动化工具包.exe
echo  Send this single file to the customer.
goto END

:FAST
echo.
echo  ==========================================
echo    Build: ONE DIR   (文件夹版, 启动最快)
echo  ==========================================
echo.

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo  Installing PyInstaller ...
    python -m pip install pyinstaller
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller --noconfirm --clean --onedir --console ^
    --name office-tools ^
    --hidden-import openpyxl ^
    --hidden-import pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module scipy ^
    --exclude-module tkinter ^
    --exclude-module IPython ^
    --exclude-module pytest ^
    menu.py
if errorlevel 1 goto FAIL

if exist "dist\office-tools" if not exist "dist\办公自动化工具包" move "dist\office-tools" "dist\办公自动化工具包" >nul

echo.
echo  Done:  dist\办公自动化工具包\  (whole folder, do not split)
echo  Zip the folder before sending.
goto END

:FAIL
echo.
echo  [ERROR] Build failed. See messages above.
pause
exit /b 1

:END
echo.
pause
