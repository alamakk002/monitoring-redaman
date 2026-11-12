@echo off
title OptiPulse NOC
cd /d "%~dp0"
echo ================================================================
echo   Menjalankan OptiPulse NOC...
echo   Tutup jendela ini atau tekan Ctrl + C untuk menghentikan server.
echo ================================================================
echo.
python server.py
if errorlevel 1 (
  echo.
  echo Server gagal dijalankan.
  echo Pastikan Python sudah terpasang dan jalankan: pip install fastapi uvicorn netmiko
  pause
)
