@echo off
chcp 65001 >nul
title Membuat installer Daily App
cd /d "%~dp0"

echo ============================================================
echo.
echo            Membuat installer Daily App
echo            (butuh beberapa menit, jangan tutup jendela ini)
echo.
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv tidak ditemukan. Lihat docs\PENGEMBANG.md bagian instalasi.
    pause
    exit /b 1
)

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [ERROR] Inno Setup 6 belum terpasang. Pasang dengan perintah:
    echo   winget install --id JRSoftware.InnoSetup -e --source winget
    pause
    exit /b 1
)

rem Ambil nomor versi dari app\version.py
rem (path relatif tanpa tanda kutip: cmd melepas kutip ganda di dalam for /f)
for /f "usebackq delims=" %%v in (`.venv\Scripts\python.exe -c "from app.version import __version__; print(__version__)"`) do set "APPVER=%%v"
echo Versi: %APPVER%
echo.

echo [1/3] Memastikan dependency build terpasang...
".venv\Scripts\python.exe" -m pip install --quiet pyinstaller pywebview
if errorlevel 1 goto gagal

echo [2/3] Membungkus aplikasi dengan PyInstaller...
".venv\Scripts\python.exe" -m PyInstaller packaging\daily_app.spec --noconfirm --clean --distpath dist --workpath build
if errorlevel 1 goto gagal

echo [3/3] Membuat installer dengan Inno Setup...
"%ISCC%" /Q /DAppVersion=%APPVER% packaging\installer.iss
if errorlevel 1 goto gagal

echo.
echo ============================================================
echo  Selesai: dist\installer\DailyApp-Setup-%APPVER%.exe
echo  File itulah yang dibagikan ke orang lain.
echo ============================================================
echo.
explorer "dist\installer"
pause
exit /b 0

:gagal
echo.
echo [ERROR] Pembuatan installer gagal. Periksa pesan di atas.
pause
exit /b 1
