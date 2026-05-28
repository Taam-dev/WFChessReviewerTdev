#!/bin/bash
echo "============================================"
echo " WFChessReviewerTdev - Build Script"
echo "============================================"
echo ""

# Install dependencies
echo "[1/4] Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller pillow

# Install Playwright browsers
echo "[2/4] Installing Playwright Chromium..."
python -m playwright install chromium

# Build
echo "[3/4] Building executable..."
pyinstaller \
    --onefile \
    --windowed \
    --name WFChessReviewerTdev \
    --icon assets/icon.ico \
    --add-data "assets:assets" \
    --hidden-import playwright \
    --hidden-import PIL \
    main.py

# Copy extras
echo "[4/4] Copying files to dist..."
cp README.md dist/ 2>/dev/null
cp LICENSE dist/ 2>/dev/null
cp requirements.txt dist/ 2>/dev/null

echo ""
echo "============================================"
echo " Build complete! Check the dist/ folder."
echo "============================================"