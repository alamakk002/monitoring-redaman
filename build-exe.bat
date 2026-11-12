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
    --icon "assets\optipulse.ico" ^
    --add-data "index.html;." ^
    --add-data "vendor;vendor" ^
    --collect-all netmiko ^
    --exclude-module tkinter ^
    server.py
if errorlevel 1 goto :error

echo.
echo Aplikasi: dist\OptiPulse-NOC.exe

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if exist "%ISCC%" (
    echo.
    echo Membuat installer...
    "%ISCC%" installer.iss
    if errorlevel 1 goto :error
    echo Installer: dist\OptiPulse-NOC-Setup.exe
) else (
    echo.
    echo Inno Setup tidak ditemukan. Installer tidak dibuat.
    echo Unduh dari https://jrsoftware.org/isdl.php lalu jalankan build-exe.bat lagi.
)

echo.
echo Selesai.
pause
exit /b 0

:error
echo.
echo Build gagal. Periksa pesan error di atas.
pause
exit /b 1
