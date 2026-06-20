@echo off
chcp 65001 >nul
title RedVideo Build

REM === Install PyInstaller ===
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [..] Installing PyInstaller...
    pip install pyinstaller
    echo.
)

REM === Download libmpv if missing ===
if not exist bin\libmpv-2.dll (
    echo [..] Downloading libmpv...
    python scripts\setup_mpv.py
    echo.
)

REM === Build ===
echo [..] Building...
pyinstaller --onefile --windowed ^
    --name "RedVideo" ^
    --icon "resources\icon.ico" ^
    --add-data "resources;resources" ^
    --distpath dist ^
    --workpath build_tmp ^
    --noconfirm ^
    main.py

if %errorlevel% neq 0 (
    echo [!!] Build failed, error code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] Output: dist\RedVideo.exe
echo.
echo [..] Copying runtime DLLs...
if not exist dist\bin mkdir dist\bin
xcopy /y /q bin\*.dll dist\bin\ >nul 2>&1

echo.
echo ====================
echo Done! Run dist\RedVideo.exe
pause