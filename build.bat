@echo off
echo ============================================
echo  WFChessReviewerTdev - Build Script
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.8+ first.
    pause
    exit /b 1
)

:: Install dependencies
echo [1/4] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller pillow

:: Install Playwright browsers
echo [2/4] Installing Playwright Chromium...
python -m playwright install chromium

:: Build exe
echo [3/4] Building executable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name WFChessReviewerTdev ^
    --icon assets/icon.ico ^
    --add-data "assets;assets" ^
    --hidden-import playwright ^
    --hidden-import PIL ^
    main.py

:: Copy extras to dist
echo [4/4] Copying files to dist...
copy README.md dist\ >nul 2>&1
copy LICENSE dist\ >nul 2>&1
copy requirements.txt dist\ >nul 2>&1

echo.
echo ============================================
echo  Build complete! Check the dist/ folder.
echo ============================================
pause