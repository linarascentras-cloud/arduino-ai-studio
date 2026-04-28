@echo off
title Arduino AI Studio v3.0
chcp 65001 >nul 2>&1

echo.
echo  =============================================
echo    Arduino AI Studio v3.0
echo  =============================================
echo.

:: Patikrinti Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [KLAIDA] Python nerastas!
    echo Parsisiusk is: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

:: Įdiegti priklausomybes
echo.
echo [INFO] Tikriname priklausomybes...
python -m pip install customtkinter pyserial requests Pillow --quiet --disable-pip-version-check

echo [INFO] Paleidziama programa...
echo.

python launcher.py

if errorlevel 1 (
    echo.
    echo [KLAIDA] Programa uzsidarė su klaida!
    pause
)
