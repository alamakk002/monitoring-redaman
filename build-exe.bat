@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Membangun OptiPulse-NOC.exe
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python tidak ditemukan. Pasang Python dari python.org lalu coba lagi.
    pause
    exit /b 1
)

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller belum terpasang. Memasang sekarang...
    python -m pip install pyinstaller
    if errorlevel 1 goto :error
)

python -m PyInstaller --noconfirm --clean --onefile ^
    --name "OptiPulse-NOC" ^
    --add-data "index.html;." ^
    --add-data "vendor;vendor" ^
    --collect-all netmiko ^
    --exclude-module tkinter ^
    server.py
if errorlevel 1 goto :error

echo.
echo Selesai. File aplikasi: dist\OptiPulse-NOC.exe
pause
exit /b 0

:error
echo.
echo Build gagal. Periksa pesan error di atas.
pause
exit /b 1
