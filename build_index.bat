@echo off
REM İndeksleri bt-support ortamında oluştur

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
echo Indeksler olusturuluyor...
echo ========================================
echo.

python scripts/build_and_test_index.py

pause
endlocal

