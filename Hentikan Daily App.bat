@echo off
chcp 65001 >nul
title Hentikan Daily App
cd /d "%~dp0"

echo ============================================================
echo.
echo            Menghentikan Daily App...
echo.
echo ============================================================
echo.

set "FOUND="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo    Menutup proses PID %%a ...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
if not defined FOUND (
    echo    Daily App memang sedang tidak berjalan.
) else (
    echo    Daily App sudah dihentikan.
)

echo.
echo    Jendela ini akan tertutup sendiri...
timeout /t 4 /nobreak >nul 2>&1
