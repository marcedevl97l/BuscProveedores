@echo off
chcp 65001 >nul
color 0E
cls

:menu
echo.
echo ================================================================
echo    ACTUALIZAR DATOS - MENU DE OPCIONES
echo ================================================================
echo.
echo    1. Actualizar Base de Datos desde Excel
echo    2. Actualizar datos de Farmacom
echo    3. Actualizar Todo (Excel + Farmacom)
echo    4. Salir
echo.
set /p opcion="Selecciona una opcion (1-4): "

set "PYTHON_EXE=python"
if exist "%CD%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
)

if "%opcion%"=="1" goto actualizar_excel
if "%opcion%"=="2" goto actualizar_farmacom
if "%opcion%"=="3" goto actualizar_todo
if "%opcion%"=="4" goto salir

echo Opcion invalida. Intenta de nuevo.
pause
goto menu

:actualizar_excel
echo.
echo ================================================================
echo    ACTUALIZANDO BASE DE DATOS DESDE EXCEL
echo ================================================================
echo.

echo [1/2] Actualizando datos de Excel...
"%PYTHON_EXE%" recolector.py
if %ERRORLEVEL% NEQ 0 (
    echo       Error al recargar datos de Excel
    pause
    exit /b 1
)
echo.

echo ================================================================
echo    DATOS DE EXCEL ACTUALIZADOS CORRECTAMENTE
echo ================================================================
echo.
pause
goto menu

:actualizar_farmacom
echo.
echo ================================================================
echo    ACTUALIZANDO DATOS DE FARMACOM
echo ================================================================
echo.

echo [1/1] Recargando datos de Farmacom...
"%PYTHON_EXE%" scraper_farmacom.py
if %ERRORLEVEL% NEQ 0 (
    echo       Error al recargar datos de Farmacom
    pause
    exit /b 1
)
echo.

echo ================================================================
echo    DATOS DE FARMACOM ACTUALIZADOS CORRECTAMENTE
echo ================================================================
echo.
pause
goto menu

:actualizar_todo
echo.
echo ================================================================
echo    ACTUALIZANDO TODO (EXCEL + FARMACOM)
echo ================================================================
echo.

REM 1. BORRAR BASE DE DATOS VIEJA
echo [1/4] Limpiando base de datos...
if exist db.sqlite (
    del /F /Q db.sqlite
    echo       db.sqlite eliminado
)
if exist data\db.sqlite (
    del /F /Q data\db.sqlite
    echo       data\db.sqlite eliminado
)
echo.

REM 2. CREAR BASE DE DATOS NUEVA
echo [2/4] Creando base de datos...
"%PYTHON_EXE%" init_db.py
if %ERRORLEVEL% NEQ 0 (
    echo       Error al crear base de datos
    pause
    exit /b 1
)
echo.

REM 3. RECARGAR DATOS DESDE EXCEL
echo [3/4] Recargando datos de Excel...
"%PYTHON_EXE%" recolector.py
if %ERRORLEVEL% NEQ 0 (
    echo       Error al recargar datos de Excel
    pause
    exit /b 1
)
echo.

REM 4. RECARGAR DATOS DE FARMACOM
echo [4/4] Recargando datos de Farmacom...
"%PYTHON_EXE%" scraper_farmacom.py
if %ERRORLEVEL% NEQ 0 (
    echo       Error al recargar datos de Farmacom
    pause
    exit /b 1
)
echo.

echo ================================================================
echo    TODOS LOS DATOS ACTUALIZADOS CORRECTAMENTE
echo ================================================================
echo.
pause
goto menu

:salir
echo.
echo Hasta luego!
exit /b 0
