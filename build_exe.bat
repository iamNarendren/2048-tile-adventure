@echo off
REM Build the single-file Windows executable for 2048 Tile Adventure.
REM The result is dist\2048TileAdventure.exe
cd /d "%~dp0"

echo [1/4] Installing build requirements...
python -m pip install --upgrade pygame pyinstaller || goto :error

echo [2/4] Running the unit tests...
python -m pytest -q || goto :error

echo [3/4] Running the headless smoke test...
python smoke_test.py || goto :error

echo [4/4] Packaging with PyInstaller...
python -m PyInstaller 2048TileAdventure.spec --noconfirm --clean || goto :error

echo.
echo Done. The game is at: dist\2048TileAdventure.exe
pause
exit /b 0

:error
echo.
echo BUILD FAILED - read the message above.
pause
exit /b 1
