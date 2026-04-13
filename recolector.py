import pandas as pd
import sqlite3
import os
from normalizador import limpiar
from config import DB

def ensure_schema():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        codigo TEXT,
        proveedor TEXT,
        precio REAL,
        precio_escala REAL,
        fuente TEXT,
        url TEXT,
        escala TEXT,
        texto_busqueda TEXT,
        fecha_venc TEXT
    )
    """)
    c.execute("PRAGMA table_info(productos)")
    columns = [row[1] for row in c.fetchall()]
    if "url" not in columns:
        c.execute("ALTER TABLE productos ADD COLUMN url TEXT")
    if "escala" not in columns:
        c.execute("ALTER TABLE productos ADD COLUMN escala TEXT")
    if "precio_escala" not in columns:
        c.execute("ALTER TABLE productos ADD COLUMN precio_escala REAL")
    if "fecha_venc" not in columns:
        c.execute("ALTER TABLE productos ADD COLUMN fecha_venc TEXT")
    conn.commit()
    conn.close()

def limpiar_datos_excel(nombre_archivo):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    nombre_upper = nombre_archivo.upper()
    if "PIONERO" in nombre_upper:
        patron = "%PIONERO%"
    elif "PROSALUD" in nombre_upper:
        patron = "%PROSALUD%"
    else:
        patron = f"{nombre_archivo}%"
    c.execute("DELETE FROM productos WHERE fuente LIKE ?", (patron,))
    conn.commit()
    conn.close()

def guardar_producto(data):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    texto_busqueda = f"{data['nombre']} {data['codigo']} {data['proveedor']}"

    c.execute("""
        INSERT INTO productos
        (nombre, codigo, proveedor, precio, precio_escala, fuente, url, escala, texto_busqueda, fecha_venc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nombre"],
        data["codigo"],
        data["proveedor"],
        data["precio"],
        data.get("precio_escala"),
        data["fuente"],
        data["url"],
        data.get("escala"),
        limpiar(texto_busqueda),
        data.get("fecha_venc", "")
    ))

    conn.commit()
    conn.close()

def parse_str(value):
    if pd.isna(value):
        return ""
    return str(value)

def parse_float(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None

def parse_date(value):
    if pd.isna(value):
        return ""
    try:
        dt = pd.to_datetime(value, errors="coerce")
    except Exception:
        return ""
    if pd.isna(dt):
        return ""
    return dt.date().isoformat()

def leer_excel(ruta):
    ensure_schema()
    nombre_archivo = os.path.basename(ruta)
    is_pionero = "PIONERO" in nombre_archivo.upper()
    is_prosalud = "PROSALUD" in nombre_archivo.upper()

    # Limpia solo los datos que vienen de este archivo
    limpiar_datos_excel(nombre_archivo)

    hojas = pd.read_excel(ruta, sheet_name=None)
    errores = []
    guardados = 0

    for nombre_hoja, df in hojas.items():
        for idx, fila in df.iterrows():
            try:
                precio = parse_float(fila.iloc[3])
                if precio is None:
                    precio = 0.0

                escala = parse_str(fila.iloc[5]) if is_pionero else ""
                precio_escala = parse_float(fila.iloc[6]) if is_pionero else None
                
                if is_prosalud:
                    fecha_venc = parse_date(fila.iloc[5])
                elif is_pionero:
                    fecha_venc = parse_date(fila.iloc[4])
                else:
                    fecha_venc = ""

                producto = {
                    "codigo": parse_str(fila.iloc[0]),
                    "nombre": parse_str(fila.iloc[1]),
                    "proveedor": parse_str(fila.iloc[2]),
                    "precio": precio,
                    "precio_escala": precio_escala,
                    "fuente": f"{nombre_archivo} | Hoja: {nombre_hoja} | Fila: {idx + 2}",
                    "url": "",
                    "escala": escala,
                    "fecha_venc": fecha_venc
                }
                guardar_producto(producto)
                guardados += 1
            except Exception as exc:
                errores.append((nombre_hoja, idx + 2, str(exc)))

    print(f"{nombre_archivo}: {guardados} productos guardados")
    if errores:
        print(f"{nombre_archivo}: {len(errores)} filas con error")

def leer_excel_con_mapeo(ruta, mapeo):
    """
    Procesa un Excel usando un mapeo de columnas explícito.
    mapeo = {
        'nombre': 'NombreColumna',   # requerido
        'codigo': 'CodColumna',      # requerido
        'proveedor': 'ProvColumna',  # opcional
        'precio': 'PrecioColumna',   # requerido
        'fecha_venc': 'FechaCol',    # opcional, None para omitir
        'escala': 'EscalaCol',       # opcional, None para omitir
        'precio_escala': 'PECol',    # opcional, None para omitir
    }
    Devuelve (guardados, errores).
    """
    ensure_schema()
    nombre_archivo = os.path.basename(ruta)
    limpiar_datos_excel(nombre_archivo)

    hojas = pd.read_excel(ruta, sheet_name=None)
    errores = []
    guardados = 0

    for nombre_hoja, df in hojas.items():
        for idx, fila in df.iterrows():
            try:
                col_nombre = mapeo.get('nombre')
                col_codigo = mapeo.get('codigo')
                col_proveedor = mapeo.get('proveedor')
                col_precio = mapeo.get('precio')
                col_fecha_venc = mapeo.get('fecha_venc')
                col_escala = mapeo.get('escala')
                col_precio_escala = mapeo.get('precio_escala')

                nombre = parse_str(fila[col_nombre]) if col_nombre and col_nombre in fila.index else ""
                if not nombre:
                    continue

                codigo = parse_str(fila[col_codigo]) if col_codigo and col_codigo in fila.index else ""
                proveedor = parse_str(fila[col_proveedor]) if col_proveedor and col_proveedor in fila.index else ""
                precio = parse_float(fila[col_precio]) if col_precio and col_precio in fila.index else None
                precio = precio if precio is not None else 0.0
                fecha_venc = parse_date(fila[col_fecha_venc]) if col_fecha_venc and col_fecha_venc in fila.index else ""
                escala = parse_str(fila[col_escala]) if col_escala and col_escala in fila.index else ""
                precio_escala = parse_float(fila[col_precio_escala]) if col_precio_escala and col_precio_escala in fila.index else None

                producto = {
                    "codigo": codigo,
                    "nombre": nombre,
                    "proveedor": proveedor,
                    "precio": precio,
                    "precio_escala": precio_escala,
                    "fuente": f"{nombre_archivo} | Hoja: {nombre_hoja} | Fila: {idx + 2}",
                    "url": "",
                    "escala": escala,
                    "fecha_venc": fecha_venc,
                }
                guardar_producto(producto)
                guardados += 1
            except Exception as exc:
                errores.append((nombre_hoja, idx + 2, str(exc)))

    print(f"{nombre_archivo}: {guardados} productos guardados con mapeo personalizado")
    if errores:
        print(f"{nombre_archivo}: {len(errores)} filas con error")
    return guardados, errores


if __name__ == "__main__":
    leer_excel("data/PIONERO FEB26.xlsx")
    leer_excel("data/PROSALUD FEB26.xlsx")
    print("Datos de Excel actualizados sin borrar Farmacom")
