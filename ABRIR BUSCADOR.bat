@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
color 0B
cls

echo.
echo INICIO RAPIDO - Buscador de Productos
echo.

set "DB_PATH="

if exist "%CD%\db.sqlite" (
    set "DB_PATH=%CD%\db.sqlite"
    echo Base de datos encontrada: db.sqlite
)

if not defined DB_PATH if exist "%CD%\data\db.sqlite" (
    set "DB_PATH=%CD%\data\db.sqlite"
    echo Base de datos encontrada: data\db.sqlite
)

if not defined DB_PATH (
    echo ERROR: No existe la base de datos
    echo Ejecuta primero: ACTUALIZAR BASE DE DATOS.bat o init_db.py
    echo.
    pause
    goto :eof
)

echo DB_PATH = !DB_PATH!

echo Iniciando servidor...
echo Abriendo: http://localhost:5000
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

timeout /t 2 /nobreak >nul
start http://localhost:5000

set "PYTHON_EXE=python"
if exist "%CD%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
)

echo Ejecutando: %PYTHON_EXE% app.py
set "DB_PATH=!DB_PATH!"
call "%PYTHON_EXE%" app.py

echo.
echo El servidor se detuvo.
pause
