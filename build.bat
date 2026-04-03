@echo off
:: ============================================================
:: build.bat — LOGIPORT Build Script
:: يبني الـ EXE ثم الـ installer بأمر واحد
:: ============================================================
setlocal EnableDelayedExpansion

title LOGIPORT Build

echo.
echo  ╔══════════════════════════════════════╗
echo  ║     LOGIPORT Build Script            ║
echo  ╚══════════════════════════════════════╝
echo.

:: ── 1. التحقق من Python ─────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    pause & exit /b 1
)

:: ── 2. التحقق من PyInstaller ────────────────────────────────
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
)

:: ── 3. تنظيف build القديم ───────────────────────────────────
echo [STEP 1/3] Cleaning previous build...
if exist "dist\LOGIPORT" rmdir /s /q "dist\LOGIPORT"
if exist "build"         rmdir /s /q "build"

:: ── 4. بناء EXE بـ PyInstaller ──────────────────────────────
echo [STEP 2/3] Building EXE with PyInstaller...
python -m PyInstaller main.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] PyInstaller build FAILED
    pause & exit /b 1
)

echo [OK] EXE built successfully.

:: ── 5. بناء Installer بـ Inno Setup ────────────────────────
echo [STEP 3/3] Building Installer with Inno Setup...

:: ابحث عن Inno Setup في المسارات الشائعة
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "!ISCC!"=="" (
    echo [WARNING] Inno Setup not found — skipping installer build.
    echo           Download from: https://jrsoftware.org/isdl.php
    echo.
    echo [DONE] EXE is ready at: dist\LOGIPORT\LOGIPORT.exe
    pause & exit /b 0
)

"!ISCC!" installer.iss

if errorlevel 1 (
    echo [ERROR] Inno Setup build FAILED
    pause & exit /b 1
)

:: ── 6. النتيجة ──────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════╗
echo  ║  Build Complete!                     ║
echo  ╚══════════════════════════════════════╝
echo.

:: اعثر على الـ installer المُنشأ
for %%f in (dist\LOGIPORT_Setup_*.exe) do (
    echo  Installer: %%f
    echo  Size:      %%~zf bytes
)

echo.
pause