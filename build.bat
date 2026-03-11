@echo off
chcp 65001 > nul
title LOGIPORT Builder

echo ============================================================
echo   LOGIPORT v1.0.0 - Build Script
echo ============================================================
echo.

:: تأكد أن المسار صحيح
cd /d "%~dp0"

:: ── 1. تنظيف البناء القديم ────────────────────────────────────
echo [1/4] Cleaning previous build...
if exist dist\LOGIPORT (
    rmdir /s /q dist\LOGIPORT
    echo       dist\LOGIPORT deleted
)
if exist build\LOGIPORT (
    rmdir /s /q build\LOGIPORT
    echo       build\LOGIPORT deleted
)
echo       Done.
echo.

:: ── 2. بناء EXE عبر PyInstaller ──────────────────────────────
echo [2/4] Running PyInstaller...
pyinstaller main.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed! Check output above.
    pause
    exit /b 1
)
echo       EXE built successfully.
echo.

:: ── 3. تأكد أن dist\LOGIPORT\LOGIPORT.exe موجود ──────────────
if not exist dist\LOGIPORT\LOGIPORT.exe (
    echo [ERROR] LOGIPORT.exe not found in dist\LOGIPORT\
    pause
    exit /b 1
)

:: ── 4. بناء المثبّت عبر Inno Setup ──────────────────────────
echo [3/4] Building installer with Inno Setup...

:: ابحث عن ISCC في المسارات الشائعة
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo [ERROR] Inno Setup not found!
    echo         Install from: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

%ISCC% installer.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup failed!
    pause
    exit /b 1
)
echo       Installer built successfully.
echo.

:: ── 5. النتيجة النهائية ───────────────────────────────────────
echo [4/4] Done!
echo.
echo ============================================================
if exist dist\LOGIPORT_Setup_1.0.0.exe (
    echo   Output: dist\LOGIPORT_Setup_1.0.0.exe
    for %%A in (dist\LOGIPORT_Setup_1.0.0.exe) do echo   Size:   %%~zA bytes
) else (
    echo   Output: dist\ folder
)
echo ============================================================
echo.
pause
