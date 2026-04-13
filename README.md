# Buscador de Productos

Este proyecto es una aplicación web para buscar y gestionar productos, utilizando Flask como framework backend, SQLite como base de datos, y herramientas de scraping para recolectar datos.

## Requisitos del Sistema

- **Sistema Operativo**: Windows 10 o superior
- **Python**: Versión 3.8 o superior (recomendado 3.10)
- **Espacio en Disco**: Al menos 500 MB para la aplicación y dependencias
- **Conexión a Internet**: Necesaria para instalar dependencias y descargar navegadores para scraping

## Dependencias y Programas Necesarios

### Programas
- **Python**: El lenguaje de programación principal. Incluye `pip` para instalar paquetes.
- **Git** (opcional): Para clonar el repositorio si se descarga desde un control de versiones.

### Dependencias de Python (instaladas automáticamente)
- Flask: Framework web
- Flask-Login: Gestión de autenticación
- Playwright: Para automatización web y scraping
- Pandas: Manipulación de datos
- OpenPyXL: Lectura/escritura de archivos Excel
- BeautifulSoup4: Análisis de HTML
- Requests: Solicitudes HTTP
- Python-Docx: Generación de documentos Word

### Dependencias del Sistema
- Navegadores web (instalados automáticamente por Playwright): Chromium, Firefox, etc., para el scraping.

## Guía de Instalación

Sigue estos pasos para instalar y configurar el proyecto en una computadora nueva.

### Paso 1: Instalar Python
1. Ve al sitio oficial de Python: [python.org](https://www.python.org/downloads/)
2. Descarga la versión más reciente de Python 3.x (3.8 o superior).
3. Ejecuta el instalador.
4. Durante la instalación, asegúrate de marcar la opción "Add Python to PATH".
5. Verifica la instalación abriendo una terminal (PowerShell o CMD) y ejecutando:
   ```
   python --version
   pip --version
   ```

### Paso 2: Obtener el Proyecto
- Si tienes acceso al repositorio Git, clónalo:
  ```
  git clone <url-del-repositorio>
  cd "BUSCADOR V1"
  ```
- Si no, descarga el archivo ZIP del proyecto y extráelo en una carpeta, por ejemplo `C:\BUSCADOR V1`.

### Paso 3: Instalar Dependencias de Python
1. Abre una terminal en la carpeta del proyecto (por ejemplo, `C:\BUSCADOR V1`).
2. Instala las dependencias ejecutando:
   ```
   pip install -r requirements.txt
   ```
   Esto instalará todas las bibliotecas necesarias.

### Paso 4: Instalar Navegadores para Playwright (si usas scraping)
Si planeas usar el scraper (`scraper_farmacom.py`), instala los navegadores necesarios:
```
playwright install
```
Esto descargará e instalará navegadores como Chromium automáticamente.

### Paso 5: Inicializar la Base de Datos
Ejecuta el script para crear la base de datos SQLite:
```
python init_db.py
```
Esto creará el archivo `db.sqlite` con la tabla `productos`.

### Paso 6: Ejecutar la Aplicación
Inicia la aplicación web:
```
python app.py
```
Abre tu navegador y ve a `http://localhost:5000` para acceder a la aplicación.

## Uso
- La aplicación web permite buscar productos, gestionar usuarios y exportar datos.
- Para actualizar la base de datos, ejecuta `ACTUALIZAR BASE DE DATOS.bat`.
- Para abrir el buscador directamente, usa `ABRIR BUSCADOR.bat`.

## Notas Adicionales
- La configuración se encuentra en `config.py`. Asegúrate de revisar la ruta de la base de datos (`DB`).
- Si encuentras errores, verifica que todas las dependencias estén instaladas correctamente.
- Para desarrollo, considera usar un entorno virtual de Python para aislar las dependencias.

## Variables de Entorno (.env)
Crea un archivo `.env` en la raíz del proyecto (puedes usar `.env.example` como plantilla):

```
FLASK_SECRET_KEY=tu_clave_secreta
DB_PATH=RUTA\A\db.sqlite
FARMACOM_USER=tu_usuario
FARMACOM_PASS=tu_clave
FARMACOM_HEADLESS=false
DEFAULT_ADMIN_USER=SUPERVISOR
DEFAULT_ADMIN_PASS=tu_clave_admin
```

- `DB_PATH` es opcional. Si no se configura, se usa `db.sqlite` en la raíz.
- `FARMACOM_HEADLESS=false` mantiene el navegador visible; cambia a `true` para modo headless.

## Soporte
Si tienes problemas durante la instalación, verifica los logs de error en la terminal o consulta la documentación de las bibliotecas utilizadas.
