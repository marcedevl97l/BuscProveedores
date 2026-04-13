@echo off
chcp 65001 >nul
color 0B
cls

echo.
echo ================================================================
echo    INSTALADOR - BUSCADOR DE PRECIOS
echo ================================================================
echo.

REM ── 1. Verificar Python ─────────────────────────────────────────
echo [1/6] Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Python no esta instalado o no esta en el PATH.
    echo  Descargalo desde: https://www.python.org/downloads/
    echo  Asegurate de marcar "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  Encontrado: %%v
echo.

REM ── 2. Crear entorno virtual ────────────────────────────────────
echo [2/6] Creando entorno virtual (.venv)...
if exist ".venv" (
    echo  Ya existe .venv, omitiendo creacion.
) else (
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo  ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo  Entorno virtual creado.
)
echo.

REM ── 3. Instalar dependencias ────────────────────────────────────
echo [3/6] Instalando dependencias Python...
.\.venv\Scripts\python -m pip install --upgrade pip --quiet
.\.venv\Scripts\python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)
echo  Dependencias instaladas correctamente.
echo.

REM ── 4. Instalar navegador Playwright ───────────────────────────
echo [4/6] Instalando navegador Chromium para scraping...
.\.venv\Scripts\python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo  AVISO: No se pudo instalar Chromium. El scraper de Farmacom no funcionara.
    echo  Puedes intentarlo manualmente luego con: playwright install chromium
) else (
    echo  Chromium instalado.
)
echo.

REM ── 5. Crear archivo .env ───────────────────────────────────────
echo [5/6] Configurando archivo .env...
if exist ".env" (
    echo  Ya existe .env, no se sobreescribe.
) else (
    copy ".env.example" ".env" >nul
    echo  Archivo .env creado desde .env.example.
    echo.
    echo  IMPORTANTE: Edita el archivo .env con tus credenciales antes
    echo  de iniciar la aplicacion.
)
echo.

REM ── 6. Inicializar base de datos ────────────────────────────────
echo [6/6] Inicializando base de datos...
if exist "db.sqlite" (
    echo  Ya existe db.sqlite, omitiendo inicializacion.
) else (
    .\.venv\Scripts\python init_db.py
    if %ERRORLEVEL% NEQ 0 (
        echo  ERROR: No se pudo crear la base de datos.
        pause
        exit /b 1
    )
    echo  Base de datos creada.
)
echo.

REM ── Crear carpeta data si no existe ────────────────────────────
if not exist "data" mkdir data

REM ── Listo ───────────────────────────────────────────────────────
echo ================================================================
echo    INSTALACION COMPLETADA
echo ================================================================
echo.
echo  Proximos pasos:
echo    1. Edita el archivo .env con tus credenciales
echo    2. Coloca tus archivos Excel en la carpeta  data\
echo    3. Ejecuta  ABRIR BUSCADOR.bat  para iniciar
echo.
echo  Para actualizar la base de datos usa:
echo    ACTUALIZAR BASE DE DATOS.bat
echo.
pause
