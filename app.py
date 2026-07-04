import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import time
import plotly.express as px  # <-- Librería para las minigráficas estilizadas

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

# ==========================================
# BARRA LATERAL: CONFIGURACIÓN Y LOGO
# ==========================================
with st.sidebar:
    st.header("🏢 Imagen Corporativa")
    
    logo_file = st.file_uploader(
        "Sube el Logotipo de tu Empresa (PNG/JPG):",
        type=["png", "jpg", "jpeg"],
        help="Selecciona una imagen desde tu computadora o celular"
    )
    
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
        logo_html_src = "https://images.unsplash.com/photo-1516467508483-a7212febe31a?q=80&w=200&auto=format&fit=crop"
        st.info("💡 Puedes subir tu propio logo arriba. Usando logotipo predeterminado temporalmente.")
    
    st.markdown("---")
    st.header("⚙️ Copias de Seguridad")

col_title, col_logo = st.columns([4, 1])
with col_title:
    st.title("Rancho AE: Sistema de Administración Financiera")
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
# FUNCIONES DE ESTILO DE FILAS
# ==========================================
def colorear_filas_finanzas(row):
    if row['tipo'] == 'Ingreso':
        return ['background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; font-weight: bold;'] * len(row)
    elif row['tipo'] == 'Egreso':
        return ['background-color: rgba(231, 76, 60, 0.12); color: #e74c3c;'] * len(row)
    return [''] * len(row)

# ==========================================
# 4. PROCESAMIENTO Y FILTRADO TEMPORAL
# ==========================================
if not df_finanzas.empty:
    df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
    df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
    df_finanzas = df_finanzas.dropna(subset=['fecha'])
    
    st.subheader("📆 Filtro de Período Temporal")
    col_filtro, col_fechas = st.columns([2, 3])
    
    hoy = datetime.today()
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
            st.info(f"Mostrando desde: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
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
            rango_fechas = st.date_input("Selecciona el rango (Inicio - Fin):", [fecha_defecto_inicio, fecha_defecto_fin])
            if isinstance(rango_fechas, (list, tuple)):
                if len(rango_fechas) == 2:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[1], datetime.max.time())
                    st.info(f"Rango activo: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
                else:
                    st.warning("⏳ Por favor, selecciona la fecha de fin en el calendario.")
                    st.stop()
            else:
                fecha_inicio = datetime.combine(rango_fechas, datetime.min.time())
                fecha_fin = datetime.combine(rango_fechas, datetime.max.time())
                st.info(f"Rango activo: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
        else:
            st.info("Mostrando la totalidad de los datos registrados.")

    df_filtrado = df_finanzas.copy()
    try:
        if df_filtrado['fecha'].dt.tz is not None:
            df_filtrado['fecha'] = df_filtrado['fecha'].dt.tz_localize(None)
    except AttributeError:
        pass

    if periodo != "Todo el Historial":
        f_inicio_pd = pd.to_datetime(fecha_inicio)
        f_fin_pd = pd.to_datetime(fecha_fin)
        df_filtrado = df_filtrado[(df_filtrado['fecha'] >= f_inicio_pd) & (df_filtrado['fecha'] <= f_fin_pd)]

    # Cálculo de Totales del Período
    ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    por_cobrar = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
else:
    ingresos, egresos, balance_neto, por_cobrar, por_pagar = 0, 0, 0, 0, 0
    df_filtrado = pd.DataFrame()

# ==========================================
# 5. NUEVO TABLERO EJECUTIVO ESTRUCTURADO (Estilo Premium)
# ==========================================
st.markdown("### 📊 Tablero de Control Ejecutivo")
fila_tarjetas = st.columns([1.2, 1, 1.3], gap="medium")

with fila_tarjetas[0]:
    # Tarjeta 1: Dona de Distribución Financiera
    with st.container(border=True):
        st.markdown("**Distribución de Capital**")
        if ingresos > 0 or egresos > 0:
            df_pie = pd.DataFrame({"Tipo": ["Ingresos", "Egresos"], "Monto": [ingresos, egresos]})
            fig_pie = px.pie(df_pie, values="Monto", names="Tipo", hole=0.6,
                             color="Tipo", color_discrete_map={"Ingresos": "#2ecc71", "Egresos": "#e74c3c"})
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=140, showlegend=False,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
        else:
            st.caption("Sin movimientos pagados en este período.")
        st.markdown(f"<h4 style='text-align: center; margin:0;'>Neto: ${balance_neto:,.2f}</h4>", unsafe_html=True)

with fila_tarjetas[1]:
    # Tarjeta 2: Resumen Numérico de Caja Fija
    with st.container(border=True):
        st.markdown("**Capital Neto Disponible**")
        st.markdown(f"<h2 style='color:#2ecc71; margin-top:15px; margin-bottom:5px;'>${balance_neto:,.2f}</h2>", unsafe_html=True)
        st.caption("Fondos reales liquidados en el período")
        st.write("")
        st.markdown(f"📈 **Por Cobrar:** ${por_cobrar:,.2f} <br> 📉 **Por Pagar:** ${por_pagar:,.2f}", unsafe_html=True)

with fila_tarjetas[2]:
    # Tarjeta 3: Línea de Tendencia Temporal
    with st.container(border=True):
        st.markdown("**Tendencia del Flujo de Efectivo**")
        if not df_filtrado.empty:
            df_linea = df_filtrado.copy()
            df_linea['Fecha'] = df_linea['fecha'].dt.date
            df_tendencia = df_linea.groupby(['Fecha', 'tipo'])['monto'].sum().unstack().fillna(0.0).reset_index()
            if 'Ingreso' not in df_tendencia.columns: df_tendencia['Ingreso'] = 0.0
            if 'Egreso' not in df_tendencia.columns: df_tendencia['Egreso'] = 0.0
            
            fig_line = px.line(df_tendencia, x="Fecha", y=["Ingreso", "Egreso"],
                               color_discrete_map={"Ingreso": "#2ecc71", "Egreso": "#e74c3c"})
            fig_line.update_layout(margin=dict(t=5, b=5, l=5, r=5), height=130, showlegend=False,
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig_line.update_xaxes(visible=False)
            fig_line.update_yaxes(visible=False)
            st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
        else:
            st.caption("Esperando registros del período...")
        st.markdown(f"<p style='text-align: center; font-size:12px; margin:0;'>Ingresos (Verde) vs Egresos (Rojo)</p>", unsafe_html=True)

st.write("---")

# ==========================================
# 6. PESTAÑAS DE TRABAJO OPERATIVO
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# PESTAÑA FINANZAS (Estructura de Columnas Divididas)
with tabs[0]:
    col_izq_form, col_der_tabla = st.columns([1, 2], gap="large")
    
    with col_izq_form:
        st.markdown("### 📥 Registro de Movimiento")
        with st.form("form_finanzas", clear_on_submit=True):
            f_fecha = st.date_input("Fecha Transacción", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta)").strip().upper()
            f_concepto = st.text_input("Concepto / Descripción").strip()
            f_monto = st.number_input("Monto total ($)", min_value=0.0, step=100.0)
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento", datetime.today()).strftime('%Y-%m-%d')
            
            if st.form_submit_button("💾 Guardar Transacción", use_container_width=True):
                auto_id = f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}"
                nuevo_registro = {
                    "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                    "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                    "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
                }
                if guardar_registro("finanzas", nuevo_registro, "id"):
                    st.success(f"¡Registrada con ID: {auto_id}!")
                    st.session_state["mostrar_descarga"] = False
                    time.sleep(0.4)
                    st.rerun()

    with col_der_tabla:
        st.markdown("### 📋 Historial y Herramientas")
        buscar_fin = st.text_input("🔍 Filtrar historial en tiempo real...", placeholder="Escribe para buscar...").strip()
        
        if not df_filtrado.empty:
            df_vista_finanzas = df_filtrado.copy()
            df_vista_finanzas['fecha'] = df_vista_finanzas['fecha'].dt.strftime('%Y-%m-%d')
            df_vista_finanzas = df_vista_finanzas.reindex(columns=["id", "fecha", "tipo", "categoria", "concepto", "monto", "metodo_pago", "estado_deuda"])
            
            if buscar_fin:
                mascara = df_vista_finanzas.astype(str).apply(lambda x: x.str.contains(buscar_fin, case=False)).any(axis=1)
                df_vista_finanzas = df_vista_finanzas[mascara]
                
            if not df_vista_finanzas.empty:
                df_fin_estilizado = (df_vista_finanzas.style
                                     .apply(colorear_filas_finanzas, axis=1)
                                     .format({'monto': '${:,.2f}'}))
                st.dataframe(df_fin_estilizado, use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros financieros que coincidan.")
        else:
            st.info("No hay datos en el período seleccionado.")
        
        # Módulo Colapsable de Edición/Eliminación rápido
        if not df_filtrado.empty:
            with st.expander("🛠️ Panel de Modificación y Eliminación de Registros"):
                id_seleccionado = st.selectbox("Selecciona ID de Transacción a alterar:", df_filtrado['id'].unique())
                fila_sel = df_filtrado[df_filtrado['id'] == id_seleccionado].iloc[0]
                
                fecha_orig_str = fila_sel['fecha'].strftime('%Y-%m-%d') if hasattr(fila_sel['fecha'], 'strftime') else str(fila_sel['fecha'])[:10]
                
                c1, c2 = st.columns(2)
                with c1:
                    nuevo_estado = st.selectbox("Cambiar Estado a:", ["Pagado", "Pendiente"], index=0 if fila_sel['estado_deuda'] == 'Pagado' else 1)
                with c2:
                    nuevo_monto = st.number_input("Corregir Monto ($):", min_value=0.0, value=float(fila_sel['monto']))
                
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("🔄 Actualizar Datos", use_container_width=True):
                        registro_actualizado = {
                            "id": str(id_seleccionado), "fecha": fecha_orig_str, "tipo": str(fila_sel.get('tipo', '')),
                            "categoria": str(fila_sel.get('categoria', '')).strip().upper(), "concepto": str(fila_sel.get('concepto', '')).strip(),
                            "monto": float(nuevo_monto), "metodo_pago": str(fila_sel.get('metodo_pago', '')),
                            "lote_asociado": str(fila_sel.get('lote_asociado', '')), "estado_deuda": str(nuevo_estado),
                            "fecha_vencimiento": str(fila_sel.get('fecha_vencimiento', ''))
                        }
                        if guardar_registro("finanzas", registro_actualizado, "id"):
                            st.success("¡Modificado!")
                            st.session_state["mostrar_descarga"] = False
                            time.sleep(0.4)
                            st.rerun()
                with ce2:
                    if st.button("🗑️ Eliminar Transacción", use_container_width=True, type="primary"):
                        if eliminar_registro("finanzas", "id", id_seleccionado):
                            st.warning("Borrado de Base de Datos")
                            st.session_state["mostrar_descarga"] = False
                            time.sleep(0.4)
                            st.rerun()

        # Botón de Descarga del Reporte Ejecutivo HTML
        if not df_filtrado.empty:
            html_reporte = f"""
            <html>
            <head><meta charset="utf-8"><style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                h1 {{ color: #1f4e79; border-bottom: 2px solid #1f4e79; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th {{ background-color: #1f4e79; color: white; padding: 8px; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
            </style></head>
            <body>
                <h1>Reporte de Balance y Control Financiero</h1>
                <p><strong>Período:</strong> {periodo}</p>
                <h2>Resumen</h2>
                <p>Ingresos: ${ingresos:,.2f} | Egresos: ${egresos:,.2f} | Neto: ${balance_neto:,.2f}</p>
            </body></html>
            """
            st.download_button(
                label="📄 Descargar Reporte para Google Docs",
                data=html_reporte,
                file_name=f"Balance_Financiero_{hoy.strftime('%Y%m%d')}.doc",
                mime="application/msword",
                use_container_width=True
            )

# PESTAÑA EMPLEADOS
with tabs[1]:
    st.subheader("Administración de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        e_nombre = st.text_input("Nombre del Empleado").strip().upper()
        e_tel = st.text_input("Teléfono").strip()
        e_puesto = st.text_input("Puesto").strip().upper()
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre.strip() and guardar_registro("empleados", {"nombre": e_nombre, "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": datetime.today().strftime('%Y-%m-%d')}, "nombre"):
                time.sleep(0.4)
                st.rerun()
                
    buscar_emp = st.text_input("🔍 Buscar Empleado:", key="bus_emp").strip()
    df_emp_vista = df_empleados.copy()
    if buscar_emp and not df_emp_vista.empty:
        df_emp_vista = df_emp_vista[df_emp_vista.astype(str).apply(lambda x: x.str.contains(buscar_emp, case=False)).any(axis=1)]
    st.dataframe(df_emp_vista, use_container_width=True, hide_index=True)
    
    if not df_empleados.empty:
        emp_sel = st.selectbox("Selecciona Empleado para Eliminar:", df_empleados['nombre'].unique())
        if st.button("🗑️ Eliminar Empleado"):
            if eliminar_registro("empleados", "nombre", emp_sel):
                time.sleep(0.4)
                st.rerun()

# PESTAÑA CLIENTES
with tabs[2]:
    st.subheader("Registro de Clientes")
    with st.form("form_clientes", clear_on_submit=True):
        c_nombre = st.text_input("Razón Social").strip().upper()
        c_tel = st.text_input("Teléfono").strip()
        if st.form_submit_button("💾 Guardar Cliente"):
            if c_nombre.strip() and guardar_registro("clientes", {"nombre_razon": c_nombre, "telefono": c_tel}, "nombre_razon"):
                time.sleep(0.4)
                st.rerun()
                
    buscar_cli = st.text_input("🔍 Buscar Cliente:", key="bus_cli").strip()
    df_cli_vista = df_clientes.copy()
    if buscar_cli and not df_cli_vista.empty:
        df_cli_vista = df_cli_vista
