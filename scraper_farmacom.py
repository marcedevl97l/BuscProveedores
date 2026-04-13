import os
import sqlite3
import time
from playwright.sync_api import sync_playwright
from config import DB
from normalizador import limpiar

# LOGIN_URL = "https://farmacom.com.pe/pedidos/login.php"
# LISTA_URL = "https://farmacom.com.pe/pedidos/lista.php"
# USUARIO = os.getenv("FARMACOM_USER")
# CLAVE = os.getenv("FARMACOM_PASS")
# HEADLESS = os.getenv("FARMACOM_HEADLESS", "false").lower() in ("1", "true", "yes")

def obtener_config():
    """Obtiene la configuración desde la base de datos"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT clave, valor FROM configuraciones")
    config = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return config

def limpiar_datos_farmacom():
    """Elimina los datos antiguos de Farmacom antes de actualizar"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM productos WHERE fuente LIKE 'Farmacom%'")
    conn.commit()
    eliminados = c.rowcount
    conn.close()
    print(f"✓ Eliminados {eliminados} productos antiguos de Farmacom")

def guardar_producto(codigo, nombre, marca, precio, fuente, fecha_venc=""):
    """Guarda un producto en la base de datos con búsqueda optimizada"""
    # Crear texto de búsqueda (todo en minúsculas para búsqueda insensible)
    texto_busqueda = limpiar(f"{codigo} {nombre} {marca}")
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    INSERT INTO productos (codigo, nombre, proveedor, precio, fuente, texto_busqueda, fecha_venc)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (codigo, nombre, marca, precio, fuente, texto_busqueda, fecha_venc))
    conn.commit()
    conn.close()

def cargar_farmacom():
    """Carga productos desde Farmacom usando Playwright"""
    limpiar_datos_farmacom()
    
    config = obtener_config()
    usuario = config.get('farmacom_user')
    clave = config.get('farmacom_pass')
    login_url = config.get('farmacom_url_login', "https://farmacom.com.pe/pedidos/login.php")
    lista_url = config.get('farmacom_url_lista', "https://farmacom.com.pe/pedidos/lista.php")
    headless = config.get('farmacom_headless', 'false').lower() in ("1", "true", "yes")

    if not usuario or not clave:
        raise ValueError("Configura el usuario y clave de Farmacom en el Panel de Administración")
    
    print("\n" + "="*60)
    print("🚀 INICIANDO CARGA DE FARMACOM")
    print("="*60 + "\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        print("🌐 Abriendo Farmacom...")
        page.goto(login_url, timeout=60000)
        page.wait_for_load_state("networkidle")
        
        # 🔍 Detectar si ya está logueado
        if "noticias" in page.url or "lista" in page.url:
            print("✓ Sesión activa detectada, saltando login")
        else:
            print("🔐 Haciendo login...")
            try:
                page.wait_for_selector("input[type='text']", timeout=10000)
                page.fill("input[type='text']", usuario)
                page.fill("input[type='password']", clave)
                
                # Buscar el botón de submit (puede ser button o input)
                submit_button = page.query_selector("button[type='submit']")
                if not submit_button:
                    submit_button = page.query_selector("input[type='submit']")
                if not submit_button:
                    submit_button = page.query_selector("button")
                
                if submit_button:
                    submit_button.click()
                else:
                    page.keyboard.press("Enter")
                
                page.wait_for_load_state("networkidle")
                print("✓ Login exitoso")
            except Exception as e:
                print(f"⚠ Error en login: {e}")
        
        print("📋 Entrando a lista de productos...")
        
        contador_total = 0
        errores_total = 0
        pagina = 1
        max_paginas = 70  # Límite de seguridad para evitar bucles infinitos
        
        while pagina <= max_paginas:
            print(f"\n📄 Procesando página {pagina}...")
            
            # Ir a la página específica
            page.goto(f"{lista_url}?buspag={pagina}", timeout=60000)
            
            # Esperar a que cargue la tabla
            try:
                page.wait_for_selector("table", timeout=15000)
                time.sleep(3)  # Espera adicional para asegurar que todo cargó
            except:
                print("⚠ No se encontró la tabla, intentando de todas formas...")
            
            # Extraer productos de la tabla
            filas = page.query_selector_all("table tbody tr")
            
            if len(filas) == 0:
                # Intentar otra forma de seleccionar
                filas = page.query_selector_all("table tr")
                print(f"📊 Filas totales encontradas: {len(filas)}")
                # Saltar la primera fila (encabezado)
                filas = filas[1:] if len(filas) > 0 else []
            
            print(f"📊 Productos en esta página: {len(filas)}")
            
            # Si no hay productos en esta página, terminar
            if len(filas) == 0:
                print("  🛑 No hay más productos. Fin de paginación.")
                break
            
            contador_pagina = 0
            errores_pagina = 0
            
            for i, fila in enumerate(filas):
                try:
                    columnas = fila.query_selector_all("td")
                    
                    if len(columnas) < 4:
                        continue
                    
                    # Extraer datos según la estructura observada
                    codigo = columnas[0].inner_text().strip()
                    nombre = columnas[1].inner_text().strip()
                    marca = columnas[2].inner_text().strip() if len(columnas) > 2 else ""
                    
                    # El precio está en la columna 6
                    precio_txt = "0"
                    if len(columnas) > 6:
                        precio_txt = columnas[6].inner_text().strip()

                    precio_txt = precio_txt.replace("S/", "").replace(" ", "").replace(",", "")
                    try:
                        precio = float(precio_txt)
                    except:
                        precio = 0.0

                    vencimiento = ""
                    # 🔍 Extraer vencimiento del nombre: formato (MM/YY)
                    import re
                    match = re.search(r'\((\d{1,2})\/(\d{2,4})\)', nombre)
                    if match:
                        mes = match.group(1).zfill(2)
                        anio = match.group(2)
                        if len(anio) == 2:
                            anio = "20" + anio
                        vencimiento = f"{anio}-{mes}-01"
                    
                    # Si no está en el nombre, intentar en col 5 (aunque parece ser Stock)
                    if not vencimiento and len(columnas) >= 6:
                        vencimiento_raw = columnas[5].inner_text().strip()
                        if "/" in vencimiento_raw or "-" in vencimiento_raw:
                            try:
                                import pandas as pd
                                dt = pd.to_datetime(vencimiento_raw, errors='coerce')
                                if not pd.isna(dt):
                                    vencimiento = dt.date().isoformat()
                            except:
                                pass

                    # Guardar en la base de datos
                    if codigo and nombre:  # Solo guardar si tiene código y nombre
                        guardar_producto(
                            codigo,
                            nombre,
                            marca,
                            precio,
                            "Farmacom Web",
                            vencimiento
                        )
                        contador_pagina += 1
                        contador_total += 1
                        
                        # Mostrar progreso cada 50 productos
                        if contador_total % 50 == 0:
                            print(f"  ⏳ Procesados {contador_total} productos totales...")
                        
                        # Mostrar los primeros 3 productos como muestra
                        if contador_total <= 3:
                            print(f"  ✓ {codigo} - {nombre} - {marca} - S/ {precio}")
                    
                except Exception as e:
                    errores_pagina += 1
                    errores_total += 1
                    if errores_total <= 5:  # Solo mostrar los primeros 5 errores
                        print(f"  ⚠ Error en fila {i} (página {pagina}): {e}")
            
            print(f"  ✅ Página {pagina} completada: {contador_pagina} productos guardados, {errores_pagina} errores")
            
            pagina += 1
        
        browser.close()
        
        print("\n" + "="*60)
        print(f"✅ CARGA COMPLETADA")
        print(f"   • Páginas procesadas: {pagina}")
        print(f"   • Productos guardados: {contador_total}")
        print(f"   • Errores totales: {errores_total}")
        print("="*60 + "\n")

def mostrar_estadisticas():
    """Muestra estadísticas de la base de datos"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Total de productos
    c.execute("SELECT COUNT(*) FROM productos")
    total = c.fetchone()[0]
    
    # Productos por fuente
    c.execute("SELECT fuente, COUNT(*) FROM productos GROUP BY fuente")
    por_fuente = c.fetchall()
    
    # Mostrar algunos productos de Farmacom
    c.execute("SELECT nombre, codigo, proveedor, precio FROM productos WHERE fuente LIKE 'Farmacom%' LIMIT 5")
    ejemplos = c.fetchall()
    
    conn.close()
    
    print("\n📊 ESTADÍSTICAS DE LA BASE DE DATOS")
    print("="*60)
    print(f"Total de productos: {total}")
    print("\nProductos por fuente:")
    for fuente, cantidad in por_fuente:
        print(f"  • {fuente}: {cantidad}")
    
    if ejemplos:
        print("\n🔎 Ejemplos de productos de Farmacom:")
        for nombre, codigo, proveedor, precio in ejemplos:
            print(f"  • [{codigo}] {nombre} - {proveedor} - S/ {precio}")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        cargar_farmacom()
        mostrar_estadisticas()
        print("✅ Ahora puedes usar el buscador en http://localhost:5000")
        print("💡 Intenta buscar por código (ej: 29160) o nombre de producto")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()