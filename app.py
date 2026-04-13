import os
import json
import sqlite3
import math
import subprocess
from flask import Flask, render_template, request, session, redirect, url_for, send_file, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import DB
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from io import BytesIO
from normalizador import limpiar

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'super_secret_key_change_this_in_production')
VENCIMIENTO_UMBRAL_DIAS = 240


# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

def normalizar_texto_busqueda():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, nombre, codigo, proveedor, texto_busqueda FROM productos")
    rows = c.fetchall()
    updates = []
    for row_id, nombre, codigo, proveedor, texto_busqueda in rows:
        nuevo_texto = limpiar(f"{nombre} {codigo} {proveedor}")
        if texto_busqueda != nuevo_texto:
            updates.append((nuevo_texto, row_id))
    if updates:
        c.executemany("UPDATE productos SET texto_busqueda = ? WHERE id = ?", updates)
        conn.commit()
    conn.close()

ensure_schema()
normalizar_texto_busqueda()

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[2])
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Usuario o contraseña incorrecta. Por favor, vuelve a intentar.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/ping')
def ping():
    return '', 204

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    resultados = []
    sin_stock = False
    proveedores = []
    fuentes = []
    fecha_actualizacion = datetime.now().strftime("%d/%m/%Y %H:%M")
    current_q = ""
    current_proveedor = "todos"
    current_sort = "nombre_asc"
    page = 1
    per_page = 50
    total_count = 0
    total_pages = 0

    # Obtener proveedores, fuentes y etiquetas personalizadas
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT proveedor FROM productos WHERE proveedor != '' ORDER BY proveedor")
    proveedores = [row[0] for row in c.fetchall()]
    c.execute("SELECT DISTINCT fuente FROM productos ORDER BY fuente")
    fuentes_raw = [row[0] for row in c.fetchall()]
    fuentes = list(set([f.split(' | ')[0] for f in fuentes_raw]))
    c.execute("SELECT clave, valor FROM configuraciones WHERE clave LIKE 'fuente_label_%'")
    fuente_labels = {row[0].replace('fuente_label_', '', 1): row[1] for row in c.fetchall()}
    conn.close()

    if request.method == "POST":
        q_raw = request.form.get("q", "")
        current_q = q_raw
        q = limpiar(q_raw)
        current_proveedor = request.form.get("proveedor", "todos")
        current_sort = request.form.get("sort", "nombre_asc")
        page = max(1, int(request.form.get("page", 1)))

        where_clauses = []
        params = []

        if q:
            where_clauses.append("texto_busqueda LIKE ?")
            params.append(f"%{q}%")

        if current_proveedor != "todos":
            where_clauses.append("proveedor = ?")
            params.append(current_proveedor)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sort_map = {
            "nombre_asc": "nombre ASC",
            "nombre_desc": "nombre DESC"
        }
        order_by = sort_map.get(current_sort, "nombre ASC")

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        count_query = f"SELECT COUNT(*) FROM productos WHERE {where_sql}"
        c.execute(count_query, params)
        total_count = c.fetchone()[0]
        total_pages = max(1, math.ceil(total_count / per_page)) if total_count > 0 else 0

        if total_pages > 0 and page > total_pages:
            page = total_pages

        query = f"""
            SELECT
                nombre,
                codigo,
                proveedor,
                precio,
                fuente,
                escala,
                precio_escala,
                fecha_venc,
                CASE
                    WHEN fecha_venc IS NOT NULL
                        AND fecha_venc != ''
                        AND julianday(fecha_venc) - julianday('now') <= ?
                        AND julianday(fecha_venc) - julianday('now') >= 0
                    THEN 1
                    ELSE 0
                END AS vencimiento_proximo
            FROM productos
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        params_query = [VENCIMIENTO_UMBRAL_DIAS] + params + [per_page, (page - 1) * per_page]

        c.execute(query, params_query)
        resultados = c.fetchall()
        conn.close()

        if total_count == 0:
            sin_stock = True

    return render_template(
        "index.html",
        resultados=resultados,
        sin_stock=sin_stock,
        proveedores=proveedores,
        fuentes=fuentes,
        fuente_labels=fuente_labels,
        fecha_actualizacion=fecha_actualizacion,
        current_q=current_q,
        current_proveedor=current_proveedor,
        current_sort=current_sort,
        page=page,
        per_page=per_page,
        total_count=total_count,
        total_pages=total_pages
    )

@app.route('/export_cart', methods=['POST'])
@login_required
def export_cart():
    cart_data = request.get_json()
    if not cart_data:
        return {'error': 'No cart data provided'}, 400

    # Crear workbook Excel
    wb = Workbook()
    
    # Hoja principal
    ws_main = wb.active
    ws_main.title = "Lista de Compras"
    
    # Agregar fecha y hora
    now = datetime.now()
    ws_main['A1'] = f'Fecha y hora: {now.strftime("%d/%m/%Y %H:%M")}'
    ws_main['A1'].font = Font(bold=True)
    
    # Headers
    ws_main['A3'] = 'Fuente'
    ws_main['B3'] = 'Producto'
    ws_main['C3'] = 'Laboratorio'
    ws_main['D3'] = 'Cantidad'
    for cell in ['A3', 'B3', 'C3', 'D3']:
        ws_main[cell].font = Font(bold=True)
        ws_main[cell].alignment = Alignment(horizontal='center')
    
    # Agrupar por fuente (usando solo el nombre principal)
    fuentes = {}
    total_general = 0

    for item in cart_data:
        fuente_main = item['fuente'].split(' | ')[0]
        if fuente_main not in fuentes:
            fuentes[fuente_main] = []
        fuentes[fuente_main].append(item)
        total_general += item['subtotal']

    # Llenar la hoja principal
    row = 4
    for fuente, items in fuentes.items():
        # Encabezado de fuente
        ws_main[f'A{row}'] = fuente
        ws_main[f'A{row}'].font = Font(bold=True)
        row += 1
        
        for item in items:
            ws_main[f'B{row}'] = item['nombre']
            ws_main[f'C{row}'] = item['proveedor']
            ws_main[f'D{row}'] = item['cantidad']
            row += 1
        
        row += 1  # Espacio entre grupos

    # Total general
    ws_main[f'A{row}'] = 'TOTAL GENERAL'
    ws_main[f'A{row}'].font = Font(bold=True)
    ws_main[f'D{row}'] = f'S/ {total_general:.2f}'
    row += 1

    # Hoja de proveedores (Detalle por Laboratorio)
    ws_prov = wb.create_sheet("Detalle por Laboratorio")
    ws_prov['A1'] = 'Producto'
    ws_prov['B1'] = 'Laboratorio'
    ws_prov['C1'] = 'Cantidad'
    for cell in ['A1', 'B1', 'C1']:
        ws_prov[cell].font = Font(bold=True)
        ws_prov[cell].alignment = Alignment(horizontal='center')
    
    row = 2
    for item in cart_data:
        ws_prov[f'A{row}'] = item['nombre']
        ws_prov[f'B{row}'] = item['proveedor']
        ws_prov[f'C{row}'] = item['cantidad']
        row += 1

    # Ajustar ancho de columnas
    for ws in [ws_main, ws_prov]:
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 15

    # Guardar en memoria
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    return send_file(bio, as_attachment=True, download_name='lista_compras.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/admin')
@login_required
def admin():
    # Solo el admin por defecto puede entrar (o implementar roles)
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT clave, valor FROM configuraciones")
    config_data = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    
    # Listar archivos Excel en /data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    excel_files = [f for f in os.listdir(data_dir) if f.endswith('.xlsx')]

    conn2 = sqlite3.connect(DB)
    c2 = conn2.cursor()
    c2.execute("SELECT clave, valor FROM configuraciones WHERE clave LIKE 'fuente_label_%'")
    fuente_labels = {row[0].replace('fuente_label_', '', 1): row[1] for row in c2.fetchall()}
    conn2.close()

    return render_template('admin.html', config_data=config_data, excel_files=excel_files, fuente_labels=fuente_labels)

@app.route('/admin/save_config', methods=['POST'])
@login_required
def save_config():
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        return redirect(url_for('index'))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    for clave, valor in request.form.items():
        c.execute("INSERT OR REPLACE INTO configuraciones (clave, valor) VALUES (?, ?)", (clave, valor))
    conn.commit()
    conn.close()
    flash('Configuración guardada correctamente.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/upload_excel', methods=['POST'])
@login_required
def upload_excel():
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        return redirect(url_for('index'))
    
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Archivo no válido.', 'error')
        return redirect(url_for('admin'))
    
    if file and file.filename.endswith('.xlsx'):
        filename = secure_filename(file.filename)
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        filepath = os.path.join(data_dir, filename)
        file.save(filepath)
        
        # Intentar procesar el archivo automáticamente
        try:
            from recolector import leer_excel
            leer_excel(filepath)
            flash(f'Archivo {filename} subido y procesado correctamente.', 'success')
        except Exception as e:
            flash(f'Archivo subido pero error al procesar: {e}', 'error')
            
    return redirect(url_for('admin'))

@app.route('/admin/preview_excel', methods=['POST'])
@login_required
def preview_excel():
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        return jsonify({'error': 'No autorizado'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No se seleccionó archivo'}), 400

    file = request.files['file']
    if not file.filename or not file.filename.endswith('.xlsx'):
        return jsonify({'error': 'Solo se aceptan archivos .xlsx'}), 400

    filename = secure_filename(file.filename)
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, filename)
    file.save(filepath)

    import pandas as pd
    hojas_info = {}
    try:
        hojas = pd.read_excel(filepath, sheet_name=None, nrows=4)
        for nombre_hoja, df in hojas.items():
            headers = [str(c) for c in df.columns.tolist()]
            preview = []
            for _, row in df.head(3).iterrows():
                preview.append([("" if (hasattr(v, '__class__') and v.__class__.__name__ == 'float' and str(v) == 'nan') else str(v)) for v in row.tolist()])
            hojas_info[nombre_hoja] = {'headers': headers, 'preview': preview}
    except Exception as e:
        return jsonify({'error': f'No se pudo leer el archivo: {e}'}), 400

    return jsonify({'filename': filename, 'hojas': hojas_info})


@app.route('/admin/process_mapped_excel', methods=['POST'])
@login_required
def process_mapped_excel():
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 403

    data = request.get_json()
    filename = data.get('filename', '')
    mapeo = data.get('mapeo', {})

    if not filename or not mapeo.get('nombre') or not mapeo.get('precio'):
        return jsonify({'status': 'error', 'message': 'Faltan campos requeridos (nombre, precio).'})

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    filepath = os.path.join(data_dir, secure_filename(filename))

    if not os.path.exists(filepath):
        return jsonify({'status': 'error', 'message': 'Archivo no encontrado en el servidor.'})

    try:
        from recolector import leer_excel_con_mapeo
        guardados, errores = leer_excel_con_mapeo(filepath, mapeo)
        msg = f'{guardados} productos importados correctamente.'
        if errores:
            msg += f' ({len(errores)} filas con error)'
        return jsonify({'status': 'success', 'message': msg})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/admin/save_fuente_nombre', methods=['POST'])
@login_required
def save_fuente_nombre():
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 403
    data = request.get_json()
    filename = data.get('filename', '').strip()
    nombre = data.get('nombre', '').strip()
    if not filename:
        return jsonify({'status': 'error', 'message': 'Archivo no especificado.'})
    clave = f'fuente_label_{filename}'
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if nombre:
        c.execute("INSERT OR REPLACE INTO configuraciones (clave, valor) VALUES (?, ?)", (clave, nombre))
    else:
        c.execute("DELETE FROM configuraciones WHERE clave = ?", (clave,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Nombre actualizado para "{filename}".'})


@app.route('/admin/delete_excel', methods=['POST'])
@login_required
def delete_excel():
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 403

    data = request.get_json()
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'status': 'error', 'message': 'Nombre de archivo no especificado.'})

    filename = secure_filename(filename)
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    filepath = os.path.join(data_dir, filename)

    # Borrar productos de la DB
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    nombre_upper = filename.upper()
    if "PIONERO" in nombre_upper:
        patron = "%PIONERO%"
    elif "PROSALUD" in nombre_upper:
        patron = "%PROSALUD%"
    else:
        patron = f"{filename}%"
    c.execute("DELETE FROM productos WHERE fuente LIKE ?", (patron,))
    eliminados = c.rowcount
    conn.commit()
    conn.close()

    # Borrar archivo físico
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'status': 'success', 'message': f'"{filename}" eliminado. {eliminados} productos removidos de la base de datos.'})
    else:
        return jsonify({'status': 'success', 'message': f'Productos de "{filename}" eliminados ({eliminados} registros). El archivo ya no existía en disco.'})


@app.route('/admin/run_process', methods=['POST'])
@login_required
def run_process():
    if current_user.username != os.getenv("DEFAULT_ADMIN_USER", "SUPERVISOR"):
        return jsonify({'status': 'error', 'message': 'No autorizado'})
    
    data = request.get_json()
    p_type = data.get('type')
    filename = data.get('filename')
    
    try:
        if p_type == 'farmacom':
            # Ejecutar scraper_farmacom.py como subproceso
            subprocess.Popen(['python', 'scraper_farmacom.py'])
            return jsonify({'status': 'success', 'message': 'Scraper de Farmacom iniciado en segundo plano.'})
        
        elif p_type == 'excel' and filename:
            from recolector import leer_excel
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            filepath = os.path.join(data_dir, filename)
            leer_excel(filepath)
            return jsonify({'status': 'success', 'message': f'Archivo {filename} recargado correctamente.'})
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

    return jsonify({'status': 'error', 'message': 'Acción no reconocida'})

if __name__ == "__main__":
    app.run(debug=True)
