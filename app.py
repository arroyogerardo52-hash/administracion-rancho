import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import time

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

# ==========================================
# BARRA LATERAL: CONFIGURACIÓN Y LOGO
# ==========================================
with st.sidebar:
    st.header("🏢 Imagen Corporativa")
    
    # Opción para cargar el logotipo desde el dispositivo
    logo_file = st.file_uploader(
        "Sube el Logotipo de tu Empresa (PNG/JPG):",
        type=["png", "jpg", "jpeg"],
        help="Selecciona una imagen desde tu computadora o celular"
    )
    
    # Procesar la imagen cargada y convertirla a Base64 para incrustarla en el HTML
    logo_html_src = ""
    if logo_file is not None:
        try:
            bytes_data = logo_file.getvalue()
            base64_encoded = base64.b64encode(bytes_data).decode("utf-8")
            mime_type = logo_file.type
            logo_html_src = f"data:{mime_type};base64,{base64_encoded}"
            st.image(bytes_data, width=150, caption="Logotipo cargado")
        except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")
    else:
        # Imagen de respaldo por si no se sube un archivo
        logo_html_src = "https://images.unsplash.com/photo-1516467508483-a7212febe31a?q=80&w=200&auto=format&fit=crop"
        st.info("💡 Puedes subir tu propio logo arriba. Usando logotipo predeterminado temporalmente.")
    
    st.markdown("---")
    st.header("⚙️ Copias de Seguridad")

# Título Principal con Logo Integrado
col_title, col_logo = st.columns([4, 1])
with col_title:
    st.title("Rancho AE: Sistema de Administración")
with col_logo:
    if logo_file is not None:
        st.image(logo_file, width=100)

st.markdown("---")

# ==========================================
# 2. VALIDACIÓN DE CREDENCIALES SUPABASE
# ==========================================
credentials_ready = False
if "supabase" in st.secrets:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        if url and key and "supabase.co" in url:
            credentials_ready = True
        else:
            st.error("❌ La URL de Supabase parece tener un formato incorrecto.")
    except KeyError:
        st.error("❌ Error de formato en los Secrets.")
else:
    st.warning("⚠️ Conexión pendiente: Configura Supabase en los Secrets.")

if not credentials_ready:
    st.stop()

# ==========================================
# 3. CONEXIÓN A LA BASE DE DATOS
# ==========================================
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"Error de inicialización: {e}")
        return None

supabase: Client = init_connection()
if supabase is None:
    st.stop()

def cargar_tabla(nombre_tabla):
    try:
        response = supabase.table(nombre_tabla).select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer {nombre_tabla}: {e}")
        return pd.DataFrame()

def guardar_registro(nombre_tabla, datos, llave_primaria):
    try:
        supabase.table(nombre_tabla).upsert(datos, on_conflict=llave_primaria).execute()
        return True
    except Exception as e:
        st.error(f"Error al guardar en {nombre_tabla}: {e}")
        return False

def eliminar_registro(nombre_tabla, columna_llave, valor_llave):
    try:
        supabase.table(nombre_tabla).delete().eq(columna_llave, valor_llave).execute()
        return True
    except Exception as e:
        st.error(f"Error al eliminar en {nombre_tabla}: {e}")
        return False

# Carga de tablas globales
df_finanzas = cargar_tabla("finanzas")
df_empleados = cargar_tabla("empleados")
df_clientes = cargar_tabla("clientes")
df_proveedores = cargar_tabla("proveedores")
df_lotes = cargar_tabla("lotes")

if "reporte_html" not in st.session_state:
    st.session_state["reporte_html"] = ""
if "mostrar_descarga" not in st.session_state:
    st.session_state["mostrar_descarga"] = False

# ==========================================
# 4. PANEL DE BALANCE GLOBAL & ESTADÍSTICAS
# ==========================================
st.header("📊 Balance y Control General Financiero")

if not df_finanzas.empty:
    # ---------------------------------------------------------
    # PRE-PROCESAMIENTO SEGURO DE DATOS
    # ---------------------------------------------------------
    df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
    
    # Forzamos conversión a datetime y limpiamos nulos
    df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
    df_finanzas = df_finanzas.dropna(subset=['fecha'])
    
    # ---------------------------------------------------------
    # CONFIGURACIÓN Y FILTRO DE TIEMPO
    # ---------------------------------------------------------
    st.subheader("📆 Filtro de Período Temporal")
    col_filtro, col_fechas = st.columns([2, 3])
    
    hoy = datetime.today()
    
    # Valores base por defecto (abarcando todo el día actual)
    fecha_inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_fin = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)

    with col_filtro:
        periodo = st.selectbox(
            "Selecciona el período visualizado:",
            ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"]
        )

    with col_fechas:
        if periodo == "Esta Semana":
            lunes = hoy - timedelta(days=hoy.weekday())
            fecha_inicio = lunes.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = (lunes + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            st.info(f"Mostrando desde el lunes: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
            
        elif periodo == "Este Mes":
            fecha_inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = hoy.replace(day=28) + timedelta(days=4)
            ultimo_dia = next_month - timedelta(days=next_month.day)
            fecha_fin = ultimo_dia.replace(hour=23, minute=59, second=59, microsecond=999999)
            st.info(f"Mostrando el mes en curso: **{fecha_inicio.strftime('%B %Y')}**")
            
        elif periodo == "Este Año":
            fecha_inicio = hoy.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = hoy.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
            st.info(f"Mostrando el año en curso: **{hoy.year}**")
            
        elif periodo == "Rango Personalizado":
            fecha_defecto_inicio = (hoy - timedelta(days=30)).date()
            fecha_defecto_fin = hoy.date()
            
            rango_fechas = st.date_input(
                "Selecciona el rango (Inicio - Fin):", 
                [fecha_defecto_inicio, fecha_defecto_fin],
                help="Selecciona tanto la fecha de inicio como la de fin en el calendario."
            )
            
            # Controlamos si el usuario seleccionó un rango completo o solo una fecha
            if isinstance(rango_fechas, (list, tuple)):
                if len(rango_fechas) == 2:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[1], datetime.max.time())
                elif len(rango_fechas) == 1:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[0], datetime.max.time())
            else:
                fecha_inicio = datetime.combine(rango_fechas, datetime.min.time())
                fecha_fin = datetime.combine(rango_fechas, datetime.max.time())
                
            st.info(f"Rango activo: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
        else:
            st.info("Mostrando la totalidad de los datos registrados.")

    # ---------------------------------------------------------
    # NORMALIZACIÓN Y FILTRADO SEGURO DE FECHAS
    # ---------------------------------------------------------
    df_filtrado = df_finanzas.copy()
    
    # Removemos la zona horaria de raíz de forma segura para evitar conflictos de tipo
    try:
        if df_filtrado['fecha'].dt.tz is not None:
            df_filtrado['fecha'] = df_filtrado['fecha'].dt.tz_localize(None)
    except AttributeError:
        # Si ya es datetime sin zona horaria, evitamos que rompa la ejecución
        pass

    # Aplicamos la máscara de filtrado temporal si corresponde
    if periodo != "Todo el Historial":
        f_inicio_pd = pd.to_datetime(fecha_inicio)
        f_fin_pd = pd.to_datetime(fecha_fin)
        
        df_filtrado = df_filtrado[
            (df_filtrado['fecha'] >= f_inicio_pd) & 
            (df_filtrado['fecha'] <= f_fin_pd)
        ]

    # ---------------------------------------------------------
    # CÁLCULO DE MÉTRICAS FINANCIERAS (DATOS FILTRADOS)
    # ---------------------------------------------------------
    ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    
    por_cobrar = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    
    # ---------------------------------------------------------
    # DESPLIEGUE EN INTERFAZ
    # ---------------------------------------------------------
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🟢 Ingresos Reales", f"${ingresos:,.2f}")
    m2.metric("🔴 Egresos Reales", f"${egresos:,.2f}")
    
    # Delta dinámico para el balance neto (Verde si es positivo, Rojo si es negativo)
    m3.metric(
        "💰 Balance Neto", 
        f"${balance_neto:,.2f}", 
        delta=f"${balance_neto:,.2f}" if balance_neto >= 0 else f"${balance_neto:,.2f}", 
        delta_color="normal" if balance_neto >= 0 else "inverse"
    )
    m4.metric("📈 Por Cobrar", f"${por_cobrar:,.2f}")
    m5.metric("📉 Por Pagar", f"${por_pagar:,.2f}")
else:
    st.warning("No se encontraron registros financieros para procesar en el sistema.")
# ==========================================
# 5. PESTAÑAS OPERATIVAS
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# PESTAÑA FINANZAS
with tabs[0]:
    st.subheader("Registro Financiero Automático")
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_fecha = st.date_input("Fecha Transacción", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta Animales)")
            f_concepto = st.text_input("Concepto / Descripción")
        with col2:
            f_monto = st.number_input("Monto total ($)", min_value=0.0, step=100.0)
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Transacción"):
            auto_id = f"TRA-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 100000}"
            nuevo_registro = {
                "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
            }
            if guardar_registro("finanzas", nuevo_registro, "id"):
                st.success(f"¡Transacción registrada con ID: {auto_id}!")
                st.session_state["mostrar_descarga"] = False
                st.rerun()

    st.markdown("### Historial de Movimientos")
    if not df_finanzas.empty:
        df_vista_finanzas = df_finanzas.copy()
        df_vista_finanzas['fecha'] = df_vista_finanzas['fecha'].dt.strftime('%Y-%m-%d')
        df_vista_finanzas = df_vista_finanzas.reindex(columns=["id", "fecha", "tipo", "categoria", "concepto", "monto", "metodo_pago", "lote_asociado", "estado_deuda", "fecha_vencimiento"])
        st.dataframe(df_vista_finanzas, use_container_width=True, hide_index=True)

    # =========================================================
    # SECCIÓN APARTADO: MODIFICAR O ELIMINAR TRANSACCIÓN
    # =========================================================
    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        
        id_seleccionado = st.selectbox("Selecciona ID a alterar:", df_finanzas['id'].unique(), key="del_fin")
        fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
        fecha_orig_str = fila_sel['fecha'].strftime('%Y-%m-%d') if isinstance(fila_sel['fecha'], datetime) else str(fila_sel['fecha'])
        
        c1, c2, c3 = st.columns([2, 2, 1])
        lista_estados = ["Pagado", "Pendiente"]
        idx_estado = lista_estados.index(fila_sel['estado_deuda']) if fila_sel['estado_deuda'] in lista_estados else 0
        
        with c1:
            nuevo_estado = st.selectbox(
                "Cambiar Estado Pago a:", 
                lista_estados, 
                index=idx_estado, 
                key=f"est_fin_{id_seleccionado}"
            )
        with c2:
            nuevo_monto = st.number_input(
                "Corregir Monto ($):", 
                min_value=0.0, 
                value=float(fila_sel['monto']), 
                step=100.0,
                key=f"mon_fin_{id_seleccionado}"
            )
        with c3:
            st.write("")
            st.write("")
            
            if st.button("🔄 Actualizar", key=f"btn_up_fin_{id_seleccionado}", use_container_width=True):
                registro_actualizado = {
                    "id": str(id_seleccionado),
                    "fecha": fecha_orig_str,
                    "tipo": str(fila_sel.get('tipo', '')),
                    "categoria": str(fila_sel.get('categoria', '')),
                    "concepto": str(fila_sel.get('concepto', '')),
                    "monto": float(nuevo_monto),
                    "metodo_pago": str(fila_sel.get('metodo_pago', '')),
                    "lote_asociado": str(fila_sel.get('lote_asociado', '')),
                    "estado_deuda": str(nuevo_estado),
                    "fecha_vencimiento": str(fila_sel.get('fecha_vencimiento', ''))
                }
                
                if guardar_registro("finanzas", registro_actualizado, "id"):
                    st.success("¡Registro modificado con éxito!")
                    st.session_state["mostrar_descarga"] = False
                    time.sleep(0.5)
                    st.rerun()
            
            if st.button("🗑️ Eliminar", key=f"btn_del_fin_{id_seleccionado}", use_container_width=True, type="primary"):
                if eliminar_registro("finanzas", "id", id_seleccionado):
                    st.warning("Registro eliminado de la base de datos.")
                    st.session_state["mostrar_descarga"] = False
                    time.sleep(0.5)
                    st.rerun()

# PESTAÑA EMPLEADOS
with tabs[1]:
    st.subheader("Administración de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        e_nombre = st.text_input("Nombre del Empleado")
        e_tel = st.text_input("Teléfono")
        e_puesto = st.text_input("Puesto")
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre.strip() and guardar_registro("empleados", {"nombre": e_nombre.strip(), "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": datetime.today().strftime('%Y-%m-%d')}, "nombre"):
                st.rerun()
    st.dataframe(df_empleados, use_container_width=True, hide_index=True)
    if not df_empleados.empty:
        emp_sel = st.selectbox("Selecciona Empleado para Eliminar:", df_empleados['nombre'].unique())
        if st.button("🗑️ Eliminar Empleado"):
            if eliminar_registro("empleados", "nombre", emp_sel):
                st.rerun()

# PESTAÑA CLIENTES
with tabs[2]:
    st.subheader("Registro de Clientes")
    with st.form("form_clientes", clear_on_submit=True):
        c_nombre = st.text_input("Razón Social")
        c_tel = st.text_input("Teléfono")
        if st.form_submit_button("💾 Guardar Cliente"):
            if c_nombre.strip() and guardar_registro("clientes", {"nombre_razon": c_nombre.strip(), "telefono": c_tel}, "nombre_razon"):
                st.rerun()
    st.dataframe(df_clientes, use_container_width=True, hide_index=True)
    if not df_clientes.empty:
        cli_sel = st.selectbox("Selecciona Cliente para Eliminar:", df_clientes['nombre_razon'].unique())
        if st.button("🗑️ Eliminar Cliente"):
            if eliminar_registro("clientes", "nombre_razon", cli_sel):
                st.rerun()

# PESTAÑA PROVEEDORES
with tabs[3]:
    st.subheader("Catálogo de Proveedores")
    with st.form("form_proveedores", clear_on_submit=True):
        p_nombre = st.text_input("Nombre del Proveedor / Razón Social")
        p_insumo = st.text_input("Insumo Principal (Ej: Alimento, Medicinas, Diésel)")
        p_contacto = st.text_input("Información de Contacto (Teléfono / Correo)")
        
        if st.form_submit_button("💾 Guardar Proveedor"):
            if p_nombre.strip():
                datos_proveedor = {
                    "nombre_proveedor": p_nombre.strip(), 
                    "insumo_principal": p_insumo,
                    "contacto": p_contacto
                }
                if guardar_registro("proveedores", datos_proveedor, "nombre_proveedor"):
                    st.success("Proveedor guardado correctamente.")
                    st.rerun()
                    
    if not df_proveedores.empty:
        columnas_prov = ["nombre_proveedor", "insumo_principal"]
        if "contacto" in df_proveedores.columns:
            columnas_prov.append("contacto")
        st.dataframe(df_proveedores.reindex(columns=columnas_prov), use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_proveedores, use_container_width=True, hide_index=True)
        
    if not df_proveedores.empty:
        prov_sel = st.selectbox("Selecciona Proveedor para Eliminar:", df_proveedores['nombre_proveedor'].unique())
        if st.button("🗑️ Eliminar Proveedor"):
            if eliminar_registro("proveedores", "nombre_proveedor", prov_sel):
                st.rerun()

# PESTAÑA LOTES
with tabs[4]:
    st.subheader("Control de Lotes de Ganado")
    with st.form("form_lotes", clear_on_submit=True):
        l_nombre = st.text_input("Código del Lote (Ej: Lote_Sardo_01)")
        l_desc = st.text_area("Descripción")
        if st.form_submit_button("💾 Guardar Lote"):
            if l_nombre.strip() and guardar_registro("lotes", {"nombre_lote": l_nombre.strip(), "descripcion_notas": l_desc, "fecha_creacion": datetime.today().strftime('%Y-%m-%d')}, "nombre_lote"):
                st.rerun()
    st.dataframe(df_lotes, use_container_width=True, hide_index=True)
    if not df_lotes.empty:
        lote_sel = st.selectbox("Selecciona Lote para Eliminar:", df_lotes['nombre_lote'].unique())
        if st.button("🗑️ Eliminar Lote"):
            if eliminar_registro("lotes", "nombre_lote", lote_sel):
                st.rerun()

# RESPALDO EXCEL EN SIDEBAR
with st.sidebar:
    if not df_finanzas.empty or not df_empleados.empty or not df_clientes.empty or not df_proveedores.empty or not df_lotes.empty:
        try:
            buffer = io.BytesIO()
            df_excel_fin = df_finanzas.copy()
            if 'fecha' in df_excel_fin.columns:
                df_excel_fin['fecha'] = df_excel_fin['fecha'].dt.strftime('%Y-%m-%d')
                
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_excel_fin.to_excel(writer, sheet_name='Finanzas', index=False)
                df_empleados.to_excel(writer, sheet_name='Empleados', index=False)
                df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
                df_proveedores.to_excel(writer, sheet_name='Proveedores', index=False)
                df_lotes.to_excel(writer, sheet_name='Lotes', index=False)
            st.download_button(
                label="📥 Descargar Respaldo Excel", data=buffer.getvalue(),
                file_name=f"Respaldo_Rancho_AE_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.ms-excel", use_container_width=True
            )
        except Exception:
            pass
