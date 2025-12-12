@echo off
REM Server'ı bt-support ortamında çalıştır

setlocal

set CONDA_ROOT=%USERPROFILE%\AppData\Local\anaconda3
call "%CONDA_ROOT%\Scripts\activate.bat" base
call conda activate bt-support

if %errorlevel% neq 0 (
    echo HATA: bt-support ortami aktiflestirilemedi.
    pause
    exit /b 1
)

echo ========================================
echo Server baslatiliyor...
echo ========================================
echo.

python scripts/run_server.py

pause
endlocal

