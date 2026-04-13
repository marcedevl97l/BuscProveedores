@echo off
chcp 65001 >nul
color 0E
cls

echo.
echo ================================================================
echo    REPARAR INSTALACION - BUSCADOR DE PRECIOS
echo ================================================================
echo  Usa esto si la instalacion falla o hay errores al iniciar.
echo ================================================================
echo.

echo [1/3] Recreando entorno virtual...
if exist ".venv" rmdir /s /q .venv
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python no encontrado. Instala Python 3.8+ y vuelve a intentar.
    pause
    exit /b 1
)
echo  Entorno virtual creado.
echo.

echo [2/3] Reinstalando dependencias...
.\.venv\Scripts\python -m pip install --upgrade pip --quiet
.\.venv\Scripts\python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR al instalar dependencias.
    pause
    exit /b 1
)
echo  Dependencias instaladas.
echo.

echo [3/3] Reinstalando Chromium...
.\.venv\Scripts\python -m playwright install chromium
echo.

echo ================================================================
echo    REPARACION COMPLETADA
echo ================================================================
echo.
pause
