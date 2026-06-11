@echo off
chcp 65001 >nul
title Daily App  -  JANGAN tutup jendela ini selama memakai aplikasi
cd /d "%~dp0"

echo ============================================================
echo.
echo            Daily App sedang dijalankan...
echo            Browser akan terbuka otomatis sebentar lagi.
echo.
echo            Alamat : http://localhost:8000
echo.
echo            Untuk MENGHENTIKAN aplikasi:
echo            tutup jendela ini, atau tekan CTRL + C.
echo.
echo ============================================================
echo.

REM Cek venv ada atau tidak
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment tidak ditemukan di folder .venv
    echo Jalankan dulu langkah instalasi di README.md.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" run.py

echo.
echo Daily App telah berhenti.
pause
