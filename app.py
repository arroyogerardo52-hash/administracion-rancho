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
    # Asegurar el formato correcto de datos numéricos y fechas
    df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
    df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
    
    # ---------------------------------------------------------
    # CONFIGURACIÓN Y FILTRO DE TIEMPO
    # ---------------------------------------------------------
    st.subheader("📆 Filtro de Período Temporal")
    col_filtro, col_fechas = st.columns([2, 3])
    
    hoy = datetime.today()
    fecha_inicio = hoy
    fecha_fin = hoy

    with col_filtro:
        periodo = st.selectbox(
            "Selecciona el período visualizado:",
            ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"]
        )

    with col_fechas:
        if periodo == "Esta Semana":
            fecha_inicio = hoy - timedelta(days=hoy.weekday())
            fecha_fin = fecha_inicio + timedelta(days=6)
            st.info(f"Mostrando desde el lunes: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
        elif periodo == "Este Mes":
            fecha_inicio = hoy.replace(day=1)
            next_month = hoy.replace(day=28) + timedelta(days=4)
            fecha_fin = next_month - timedelta(days=next_month.day)
            st.info(f"Mostrando el mes en curso: **{fecha_inicio.strftime('%B %Y')}**")
        elif periodo == "Este Año":
            fecha_inicio = hoy.replace(month=1, day=1)
            fecha_fin = hoy.replace(month=12, day=31)
            st.info(f"Mostrando el año en curso: **{hoy.year}**")
        elif periodo == "Rango Personalizado":
            rango_fechas = st.date_input("Selecciona el rango (Inicio - Fin):", [hoy - timedelta(days=30), hoy])
            if isinstance(rango_fechas, list) and len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = pd.to_datetime(rango_fechas[0]), pd.to_datetime(rango_fechas[1])
            elif isinstance(rango_fechas, list) and len(rango_fechas) == 1:
                fecha_inicio = pd.to_datetime(rango_fechas[0])
                fecha_fin = fecha_inicio
        else:
            st.info("Mostrando la totalidad de los datos registrados.")

    # Aplicar el filtro de fechas seleccionado al DataFrame
    if periodo != "Todo el Historial":
        df_filtrado = df_finanzas[(df_finanzas['fecha'] >= pd.to_datetime(fecha_inicio).replace(hour=0, minute=0, second=0)) & 
                                  (df_finanzas['fecha'] <= pd.to_datetime(fecha_fin).replace(hour=23, minute=59, second=59))]
    else:
        df_filtrado = df_finanzas.copy()

    # Volver a calcular métricas usando únicamente los datos filtrados
    ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    
    por_cobrar = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    
    # Renderizar tarjetas de métricas en pantalla
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🟢 Ingresos Reales", f"${ingresos:,.2f}")
    m2.metric("🔴 Egresos Reales", f"${egresos:,.2f}")
    m3.metric("💰 Balance Neto", f"${balance_neto:,.2f}", delta=f"${balance_neto:,.2f}" if balance_neto >= 0 else f"${balance_neto:,.2f}", delta_color="normal" if balance_neto >= 0 else "inverse")
    m4.metric("📈 Por Cobrar", f"${por_cobrar:,.2f}")
    m5.metric("📉 Por Pagar", f"${por_pagar:,.2f}")
    
    # ---------------------------------------------------------
    # APARTADO DE GRÁFICAS ESTADÍSTICAS
    # ---------------------------------------------------------
    st.markdown("---")
    with st.expander("📈 Ver Gráficas Estadísticas del Balance", expanded=True):
        if not df_filtrado.empty:
            g_col1, g_col2 = st.columns(2)
            
            with g_col1:
                st.markdown("##### **Flujo de Caja Absoluto (Ingresos vs Egresos)**")
                df_flujo = df_filtrado[df_filtrado['estado_deuda'] == 'Pagado'].groupby('tipo')['monto'].sum().reset_index()
                if not df_flujo.empty:
                    st.bar_chart(data=df_flujo, x='tipo', y='monto', use_container_width=True)
                else:
                    st.caption("No hay transacciones liquidadas ('Pagado') en este período para graficar el flujo.")
                    
            with g_col2:
                st.markdown("##### **Distribución de Gastos por Categoría (Egresos)**")
                df_gastos = df_filtrado[df_filtrado['tipo'] == 'Egreso'].groupby('categoria')['monto'].sum().reset_index()
                if not df_gastos.empty:
                    st.bar_chart(data=df_gastos, x='categoria', y='monto', use_container_width=True)
                else:
                    st.caption("No hay egresos registrados en este período para graficar.")
            
            # Gráfica de línea temporal de transacciones
            st.markdown("##### **Tendencia Temporal de Movimientos**")
            df_linea = df_filtrado.copy()
            df_linea['Fecha Corta'] = df_linea['fecha'].dt.strftime('%Y-%m-%d')
            df_pivot = df_linea.pivot_table(index='Fecha Corta', columns='tipo', values='monto', aggfunc='sum').fillna(0.0)
            st.line_chart(df_pivot, use_container_width=True)
        else:
            st.info("No hay datos suficientes dentro del período de tiempo seleccionado para generar analíticas.")

    # ---------------------------------------------------------
    # EXPORTACIÓN DE REPORTES (Adaptado a los datos filtrados)
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📝 Exportar Estado de Cuenta Oficial")
    if st.button("📄 Compilar Plantilla Institucional con Logotipo"):
        html_template = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.25; color: #333333; padding: 10px;">
            <table style="width: 100%; border-bottom: 2px solid #5c4033; padding-bottom: 10px;">
                <tr>
                    <td style="width: 70%; vertical-align: middle;">
                        <h1 style="margin: 0; color: #5c4033; font-size: 22pt;">RANCHO AE</h1>
                        <p style="margin: 4px 0; font-style: italic; color: #666666; font-size: 11pt;">Desarrollo Genético y Engorda Comercial</p>
                        <p style="margin: 2px 0; font-size: 11pt;"><strong>Reporte Consolidado de Administración ({periodo})</strong></p>
                    </td>
                    <td style="width: 30%; text-align: right; vertical-align: middle;">
                        <img src="{logo_html_src}" style="width: 120px; max-height: 120px; object-fit: contain;" alt="Logo">
                    </td>
                </tr>
            </table>
            
            <br>
            <p style="font-size: 10.5pt;"><strong>Fecha de Emisión:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p style="font-size: 10.5pt;">Este informe detalla el estado financiero integral extraído de forma segura desde los servidores de administración.</p>
            
            <h2 style="color: #5c4033; border-left: 4px solid #5c4033; padding-left: 8px; font-size: 14pt; margin-top: 20px;">1. Resumen de Saldos Monetarios</h2>
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%; border: 1px solid #dddddd; font-size: 11pt;">
                <thead>
                    <tr style="background-color: #f8f9fa; text-align: left;">
                        <th style="padding: 8px;">Concepto Operativo</th>
                        <th style="padding: 8px;">Monto en Cuenta</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td style="padding: 8px;">🟢 Ingresos Consolidados (Liquidados)</td><td style="padding: 8px;"><strong>${ingresos:,.2f}</strong></td></tr>
                    <tr><td style="padding: 8px;">🔴 Egresos Consolidados (Liquidados)</td><td style="padding: 8px;"><strong>${egresos:,.2f}</strong></td></tr>
                    <tr style="background-color: #f1f3f5;"><td style="padding: 8px;"><strong>💰 Balance Neto Comercial</strong></td><td style="padding: 8px;"><strong style="color: {'#2b8a3e' if balance_neto >= 0 else '#c92a2a'};">${balance_neto:,.2f}</strong></td></tr>
                    <tr><td style="padding: 8px;">📈 Cuentas Pendientes de Cobro</td><td style="padding: 8px;"><strong>${por_cobrar:,.2f}</strong></td></tr>
                    <tr><td style="padding: 8px;">📉 Cuentas Pendientes de Pago</td><td style="padding: 8px;"><strong>${por_pagar:,.2f}</strong></td></tr>
                </tbody>
            </table>
            
            <br>
            <h2 style="color: #5c4033; border-left: 4px solid #5c4033; padding-left: 8px; font-size: 14pt; margin-top: 20px;">2. Libro Diario de Transacciones</h2>
        """
        
        if not df_filtrado.empty:
            html_template += """
            <table border="1" cellpadding="6" style="border-collapse: collapse; width: 100%; border: 1px solid #dddddd; font-size: 9.5pt;">
                <thead>
                    <tr style="background-color: #f8f9fa; text-align: left;">
                        <th style="padding: 6px;">ID Código</th><th style="padding: 6px;">Fecha</th><th style="padding: 6px;">Tipo</th><th style="padding: 6px;">Categoría</th><th style="padding: 6px;">Concepto</th><th style="padding: 6px;">Monto</th><th style="padding: 6px;">Estado</th>
                    </tr>
                </thead>
                <tbody>
            """
            df_reporte_html = df_filtrado.copy()
            df_reporte_html['fecha_txt'] = df_reporte_html['fecha'].dt.strftime('%Y-%m-%d')
            
            for _, r in df_reporte_html.iterrows():
                html_template += f"""
                <tr>
                    <td style="padding: 6px;">{r.get('id','')}</td>
                    <td style="padding: 6px;">{r.get('fecha_txt','')}</td>
                    <td style="padding: 6px;">{r.get('tipo','')}</td>
                    <td style="padding: 6px;">{r.get('categoria','')}</td>
                    <td style="padding: 6px;">{r.get('concepto','')}</td>
                    <td style="padding: 6px;">${float(r.get('monto',0)):,.2f}</td>
                    <td style="padding: 6px; color: {'#2b8a3e' if r.get('estado_deuda')=='Pagado' else '#e67e22'}; font-weight: bold;">{r.get('estado_deuda','')}</td>
                </tr>
                """
            html_template += "</tbody></table>"
        
        html_template += """
            <br><br>
            <table style="width: 100%; margin-top: 40px; text-align: center; font-size: 11pt;">
                <tr>
                    <td style="width: 50%;">___________________________________<br>Dirección General de Operaciones</td>
                    <td style="width: 50%;">___________________________________<br>Control Interno y Auditoría</td>
                </tr>
            </table>
        </div>
        """
        st.session_state["reporte_html"] = html_template
        st.session_state["mostrar_descarga"] = True
        st.success("¡Estructura de la plantilla con logotipo lista para ser exportada!")

    if st.session_state["mostrar_descarga"]:
        with st.expander("👁️ Previsualizar Formato HTML del Documento", expanded=True):
            st.components.v1.html(st.session_state["reporte_html"], height=500, scrolling=True)
            
            st.markdown("### 📋 Instrucciones para copiar a Google Documentos:")
            st.info("Para llevar este reporte a Google Docs manteniendo el logotipo y los cuadros financieros intactos: "
                    "\n1. Haz clic dentro del recuadro de previsualización superior."
                    "\n2. Presiona `Ctrl + A` (o `Cmd + A` en Mac) para seleccionar todo y luego `Ctrl + C` para copiar."
                    "\n3. Ve a tu archivo de Google Documentos vacío y presiona `Ctrl + V` para pegar de forma directa.")
else:
    st.info("💡 Registra movimientos en la pestaña de finanzas para generar el balance corporativo.")

st.markdown("---")

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
