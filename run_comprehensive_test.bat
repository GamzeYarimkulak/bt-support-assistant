@echo off
REM Kapsamlı Test Scripti - Conda Ortamı ile
echo ========================================
echo KAPSAMLI SİSTEM TESTİ
echo ========================================
echo.

REM Conda ortamını aktifleştir
call C:\Users\gamze.yarimkulak\AppData\Local\anaconda3\Scripts\activate.bat base
call conda activate bt-support

if errorlevel 1 (
    echo HATA: Conda ortami aktiflestirilemedi!
    pause
    exit /b 1
)

echo Conda ortami aktiflestirildi: bt-support
echo.

REM Test scriptini çalıştır
python scripts/comprehensive_test.py

if errorlevel 1 (
    echo.
    echo HATA: Test scripti basarisiz oldu!
    pause
    exit /b 1
)

echo.
echo Test tamamlandi!
pause
















