@echo off
chcp 65001 >nul
title RedVideo Build

echo [RedVideo] 一键编译打包
echo ======================
echo.

REM 检查依赖
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [..] 安装 PyInstaller...
    pip install pyinstaller
    echo.
)

REM 下载 libmpv（如果本地没有）
if not exist bin\libmpv-2.dll (
    echo [..] 下载 libmpv...
    python scripts\setup_mpv.py
    echo.
)

REM 编译
echo [..] 编译中...
pyinstaller --onefile --windowed ^
    --name "RedVideo" ^
    --add-data "resources;resources" ^
    --distpath dist ^
    --workpath build_tmp ^
    --specpath build_tmp ^
    --noconfirm ^
    main.py

if %errorlevel% neq 0 (
    echo [!!] 编译失败，错误码 %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] 编译完成！输出：dist\RedVideo.exe
echo.
echo [..] 复制运行时依赖...
if not exist dist\bin mkdir dist\bin
xcopy /y /q bin\*.dll dist\bin\ >nul 2>&1
xcopy /y /q bin\*.a dist\bin\ >nul 2>&1

echo.
echo ======================
echo 全部完成！运行 dist\RedVideo.exe
pause
