import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import time
import json
import os
import pytz
import numpy as np

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Rancho AE - Control Interno", 
    page_icon="🤠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# 1. BANDERAS DE PRIVACIDAD Y CARGA DE USUARIOS
# -------------------------------------------------------------
TIEMPO_EXPIRED = 300  # Tiempo en segundos para cerrar sesión (5 min)

# Cargar usuarios desde Streamlit Secrets (Nube) o fallback por defecto
if "usuarios" in st.secrets:
    USUARIOS = {str(k).strip().lower(): str(v).strip() for k, v in st.secrets["usuarios"].items()}
else:
    USUARIOS = {"gerardo": "ADMINpg120214"}

# Control del estado de la sesión
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None

def cerrar_sesion():
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.rerun()

# -------------------------------------------------------------
# 2. INYECCIÓN DE ESTILOS CSS PERSONALIZADOS (CAMBIO DE ASPECTO)
# -------------------------------------------------------------
st.markdown("""
    <style>
    /* Estilo general y paleta de colores */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    
    /* Personalización de Tarjetas / Métricas */
    div[data-testid="stMetric"] {
        background: #1a1f2c;
        border: 1px solid #2d3748;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #3182ce;
    }
    div[data-testid="stMetricValue"] {
        font-size: calc(1.1rem + 0.5vw) !important;
        font-weight: 700 !important;
        color: #63b3ed !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #a0aec0 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Botones principales y secundarios */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton>button[kind="primary"] {
        background-color: #2b6cb0;
        color: white;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #3182ce;
        box-shadow: 0 0 10px rgba(49, 130, 206, 0.5);
    }

    /* Estilo para pestañas (Tabs) */
    button[data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }
    button[aria-selected="true"] {
        background-color: #1a202c !important;
        color: #63b3ed !important;
        border-bottom: 2px solid #3182ce !important;
    }

    /* Formularios y desplegables */
    div[data-testid="stForm"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 3. PANTALLA DE LOGIN
# -------------------------------------------------------------
if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<h2 style='text-align: center; color: #63b3ed;'>🤠 Rancho AE</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center;'>Acceso al Sistema</h4>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario_ingresado = st.text_input("Usuario")
            clave_ingresada = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            
            if btn_login:
                usr_limpio = usuario_ingresado.strip().lower()
                pwd_limpia = clave_ingresada.strip()

                if usr_limpio in USUARIOS and USUARIOS[usr_limpio] == pwd_limpia:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = usr_limpio
                    st.success("¡Bienvenido!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
                    
    st.stop()

# -------------------------------------------------------------
# 4. BARRA LATERAL
# -------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 **{st.session_state.usuario_actual.capitalize()}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        cerrar_sesion()

# ==========================================
# CONEXIÓN Y CONSULTAS SUPABASE
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

# Carga global de datos
df_finanzas = cargar_tabla("finanzas")
df_empleados = cargar_tabla("empleados")
df_clientes = cargar_tabla("clientes")
df_proveedores = cargar_tabla("proveedores")
df_lotes = cargar_tabla("lotes")

# ==========================================
# NAVEGACIÓN Y RESPALDOS
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.header("🧭 Navegación")
    modulo_activo = st.radio(
        "Módulo actual:",
        [
            "📊 Dashboard & Finanzas", 
            "🤠 Personal / Empleados", 
            "🤝 Clientes", 
            "🚜 Proveedores", 
            "🐂 Control de Lotes"
        ],
        index=0
    )
    
    st.markdown("---")
    st.header("⚙️ Copias de Seguridad")
    
    if not df_finanzas.empty or not df_empleados.empty or not df_clientes.empty or not df_proveedores.empty or not df_lotes.empty:
        try:
            buffer = io.BytesIO()
            df_excel_fin = df_finanzas.copy()
            if 'fecha' in df_excel_fin.columns and not df_excel_fin.empty:
                df_excel_fin['fecha'] = pd.to_datetime(df_excel_fin['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
                
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_excel_fin.to_excel(writer, sheet_name='Finanzas', index=False)
                df_empleados.to_excel(writer, sheet_name='Empleados', index=False)
                df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
                df_proveedores.to_excel(writer, sheet_name='Proveedores', index=False)
                df_lotes.to_excel(writer, sheet_name='Lotes', index=False)
                
            st.download_button(
                label="📥 Respaldo Excel Completo", 
                data=buffer.getvalue(),
                file_name=f"Respaldo_Rancho_AE_{datetime.now().strftime('%Y-%m-%d')}.xlsx", 
                mime="application/vnd.ms-excel", 
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error al generar respaldo: {e}")

st.markdown("<h1 style='color: #63b3ed;'>Rancho AE · Panel de Control</h1>", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# FUNCIONES REPORTES HTML Y AYUDANTES
# ==========================================
def colorear_filas_finanzas(row):
    if row['tipo'] == 'Ingreso':
        return ['background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; font-weight: bold;'] * len(row)
    elif row['tipo'] == 'Egreso':
        return ['background-color: rgba(231, 76, 60, 0.12); color: #e74c3c;'] * len(row)
    return [''] * len(row)

def obtener_fecha_hora_mx():
    zona_mx = pytz.timezone('America/Mexico_City')
    return datetime.now(zona_mx).strftime('%d/%m/%Y %I:%M %p')

def clasificar_categoria(cat):
    cat_lower = str(cat).lower()
    costos_directos = ['ganado', 'alimento', 'medicina', 'veterinario', 'suplemento', 'pauta', 'lote']
    gastos_operativos = ['nómina', 'nomina', 'sueldo', 'oficina', 'mantenimiento', 'combustibles', 'flete', 'servicios', 'renta']
    
    if any(k in cat_lower for k in costos_directos):
        return ('Egreso', 'Costo Directo')
    elif any(k in cat_lower for k in gastos_operativos):
        return ('Egreso', 'Gasto Operativo')
    else:
        return ('Egreso', 'Otros')

def generar_html_docs(titulo_seccion, columnas_headers, df_datos, mapping_columnas):
    hoy_str = obtener_fecha_hora_mx()
    html = f"""
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333333; line-height: 1.6; margin: 20px; }}
            h1 {{ color: #1f4e79; border-bottom: 2px solid #1f4e79; padding-bottom: 5px; font-size: 24px; }}
            p {{ font-size: 13px; color: #555; margin: 4px 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
            th {{ background-color: #1f4e79; color: white; padding: 10px 8px; text-align: left; font-size: 13px; font-weight: bold; text-transform: uppercase; border: 1px solid #1f4e79; }}
            td {{ border: 1px solid #dddddd; padding: 8px; font-size: 12px; }}
            tr:nth-child(even) {{ background-color: #f8f9fa; }}
        </style>
    </head>
    <body>
        <h1>Reporte Institucional - {titulo_seccion}</h1>
        <p><strong>Organización:</strong> Rancho AE</p>
        <p><strong>Fecha y Hora de Emisión:</strong> {hoy_str}</p>
        <p><strong>Volumen de Registros:</strong> {len(df_datos)} elementos</p>
        <table>
            <thead><tr>
    """
    for header in columnas_headers:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    for _, fila in df_datos.iterrows():
        html += "<tr>"
        for col_bd in mapping_columnas:
            val = fila.get(col_bd, '')
            if pd.isnull(val): val = ''
            elif isinstance(val, datetime) or hasattr(val, 'strftime'): val = val.strftime('%Y-%m-%d')
            elif isinstance(val, (int, float)) and col_bd == 'monto': val = f"${val:,.2f}"
            html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</tbody></table></body></html>"
    return html

def generar_reporte_finanzas_profesional(df_datos, periodo, lote, ing, egr, net, cob, pag):
    hoy_str = obtener_fecha_hora_mx()
    df_pagados = df_datos[df_datos['estado_deuda'] == 'Pagado'].copy() if not df_datos.empty else pd.DataFrame()
    tot_ingresos = ing
    tot_costos_directos, tot_gastos_operativos, tot_otros = 0.0, 0.0, 0.0
    
    if not df_pagados.empty and 'categoria' in df_pagados.columns:
        df_pagados['Rubro'] = df_pagados['categoria'].apply(lambda x: clasificar_categoria(x)[1])
        tot_costos_directos = df_pagados[(df_pagados['tipo'] == 'Egreso') & (df_pagados['Rubro'] == 'Costo Directo')]['monto'].sum()
        tot_gastos_operativos = df_pagados[(df_pagados['tipo'] == 'Egreso') & (df_pagados['Rubro'] == 'Gasto Operativo')]['monto'].sum()
        tot_otros = df_pagados[(df_pagados['tipo'] == 'Egreso') & (df_pagados['Rubro'] == 'Otros')]['monto'].sum()
        
    utilidad_bruta = tot_ingresos - tot_costos_directos
    utilidad_neta = utilidad_bruta - tot_gastos_operativos - tot_otros
    margen_bruto = (utilidad_bruta / tot_ingresos * 100) if tot_ingresos > 0 else 0.0
    margen_neto = (utilidad_neta / tot_ingresos * 100) if tot_ingresos > 0 else 0.0

    html = f"""
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2C3E50; margin: 25px; }}
            .header-title {{ font-size: 24pt; color: #1A365D; font-weight: bold; margin: 0; }}
            .divider {{ height: 3px; background-color: #2B6CB0; margin-top: 5px; margin-bottom: 20px; }}
            .kpi-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            .kpi-card {{ background: #F8FAFC; border: 1px solid #CBD5E0; padding: 10px; text-align: center; border-top: 4px solid #2B6CB0; }}
            .kpi-title {{ font-size: 9pt; text-transform: uppercase; color: #718096; font-weight: bold; }}
            .kpi-value {{ font-size: 12pt; font-weight: bold; color: #1A365D; margin-top: 4px; }}
            .data-table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 9pt; }}
            .data-table th {{ background-color: #1A365D; color: white; padding: 8px; text-align: left; border: 1px solid #1A365D; }}
            .data-table td {{ border: 1px solid #CBD5E0; padding: 6px 8px; }}
            .text-right {{ text-align: right; }}
            .bold {{ font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header-title">RANCHO AE</div>
        <div>Informe de Balance Financiero ({periodo}) - Lote: {lote}</div>
        <div class="divider"></div>
        <table class="kpi-table">
            <tr>
                <td class="kpi-card" width="33%"><div class="kpi-title">Ingresos</div><div class="kpi-value">${ing:,.2f}</div></td>
                <td class="kpi-card" width="33%"><div class="kpi-title">Egresos</div><div class="kpi-value">${egr:,.2f}</div></td>
                <td class="kpi-card" width="33%"><div class="kpi-title">Balance Neto</div><div class="kpi-value">${net:,.2f}</div></td>
            </tr>
        </table>
        <table class="data-table">
            <thead>
                <tr><th>Fecha</th><th>Tipo</th><th>Categoría</th><th>Concepto</th><th>Estado</th><th class="text-right">Monto</th></tr>
            </thead>
            <tbody>
    """
    for _, fila in df_datos.iterrows():
        f_date = fila.get('fecha', '')
        f_str = f_date.strftime('%Y-%m-%d') if hasattr(f_date, 'strftime') else str(f_date)[:10]
        html += f"""
                <tr>
                    <td>{f_str}</td>
                    <td>{fila.get('tipo', '')}</td>
                    <td>{fila.get('categoria', '')}</td>
                    <td>{fila.get('concepto', '')}</td>
                    <td>{fila.get('estado_deuda', '')}</td>
                    <td class="text-right bold">${fila.get('monto', 0.0):,.2f}</td>
                </tr>
        """
    html += "</tbody></table></body></html>"
    return html

# ==========================================
# MÓDULO 1: DASHBOARD & FINANZAS
# ==========================================
if modulo_activo == "📊 Dashboard & Finanzas":
    st.subheader("📊 Módulo de Control Financiero")

    cat_ingresos = ["Venta de ganado", "Varios (Ingresos)", "Préstamo / Crédito recibido"]
    cat_costos_directos = ["Compra de ganado", "Alimentos", "Medicamentos", "Servicios veterinarios", "Dosis de semen", "Varios (Costos directos)"]
    cat_gastos_operativos = ["Gastos de oficina", "Arriendo", "Nomina", "Combustible", "Mantenimiento", "Pago / Abono Préstamo", "Varios (Gastos operativos)"]

    lista_clientes = ["Público en general"]
    if 'df_clientes' in locals() and not df_clientes.empty:
        col_c = 'nombre' if 'nombre' in df_clientes.columns else ('nombre_razon' if 'nombre_razon' in df_clientes.columns else df_clientes.columns[0])
        lista_clientes += [c for c in df_clientes[col_c].dropna().unique() if c != "Público en general"]

    lista_proveedores = ["Egreso general", "Institución Financiera / Banco"]
    if 'df_proveedores' in locals() and not df_proveedores.empty:
        col_p = 'nombre_proveedor' if 'nombre_proveedor' in df_proveedores.columns else df_proveedores.columns[0]
        lista_proveedores += [p for p in df_proveedores[col_p].dropna().unique() if p not in lista_proveedores]

    lista_empleados = []
    if 'df_empleados' in locals() and not df_empleados.empty:
        col_e = 'nombre' if 'nombre' in df_empleados.columns else df_empleados.columns[0]
        lista_empleados = list(df_empleados[col_e].dropna().unique())
    else:
        lista_empleados = ["Empleado General / Caja"]

    for col in ['abono_acumulado', 'id_origen_abono']:
        if not df_finanzas.empty and col not in df_finanzas.columns:
            df_finanzas[col] = 0.0 if col == 'abono_acumulado' else ""

    if not df_finanzas.empty:
        df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
        df_finanzas['abono_acumulado'] = pd.to_numeric(df_finanzas.get('abono_acumulado', 0.0), errors='coerce').fillna(0.0)
        df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
        if 'fecha_vencimiento' in df_finanzas.columns:
            df_finanzas['fecha_vencimiento'] = pd.to_datetime(df_finanzas['fecha_vencimiento'], errors='coerce')
        df_finanzas = df_finanzas.dropna(subset=['fecha'])

        hoy_dt = datetime.today()

        st.markdown("##### 🔎 Filtros del Dashboard")
        col_filtro, col_lote_filtro, col_estado_filtro, col_fechas = st.columns([2, 2, 2, 3])
        
        fecha_inicio = hoy_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = hoy_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        with col_filtro:
            periodo = st.selectbox("Período:", ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"])

        with col_lote_filtro:
            opciones_filtro_lote = ["Todos los Lotes"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_filtro_lote += list(df_lotes['nombre_lote'].dropna().unique())
            lote_seleccionado = st.selectbox("Lote:", opciones_filtro_lote)

        with col_estado_filtro:
            filtro_estado = st.selectbox("Estado:", ["Todos", "Pagado", "Pendiente"])

        with col_fechas:
            if periodo == "Esta Semana":
                lunes = hoy_dt - timedelta(days=hoy_dt.weekday())
                fecha_inicio = lunes.replace(hour=0, minute=0, second=0, microsecond=0)
                fecha_fin = (lunes + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            elif periodo == "Este Mes":
                fecha_inicio = hoy_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                next_month = hoy_dt.replace(day=28) + timedelta(days=4)
                ultimo_dia = next_month - timedelta(days=next_month.day)
                fecha_fin = ultimo_dia.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif periodo == "Este Año":
                fecha_inicio = hoy_dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                fecha_fin = hoy_dt.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
            elif periodo == "Rango Personalizado":
                fecha_defecto_inicio = (hoy_dt - timedelta(days=30)).date()
                fecha_defecto_fin = hoy_dt.date()
                rango_fechas = st.date_input("Rango:", [fecha_defecto_inicio, fecha_defecto_fin])
                if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[1], datetime.max.time())

        df_filtrado = df_finanzas.copy()
        if periodo != "Todo el Historial":
            df_filtrado = df_filtrado[(df_filtrado['fecha'] >= pd.to_datetime(fecha_inicio)) & (df_filtrado['fecha'] <= pd.to_datetime(fecha_fin))]

        if lote_seleccionado != "Todos los Lotes" and 'lote_asociado' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['lote_asociado'] == lote_seleccionado]

        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['estado_deuda'] == filtro_estado]

        ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado') & (df_filtrado['categoria'] != 'Préstamo / Crédito recibido')]['monto'].sum()
        egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
        balance_neto = ingresos - egresos
        
        df_pend_ing = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente') & (df_filtrado['categoria'] != 'Préstamo / Crédito recibido')]
        por_cobrar = (df_pend_ing['monto'] - df_pend_ing['abono_acumulado']).sum() if not df_pend_ing.empty else 0.0

        df_pend_egr = df_filtrado[((df_filtrado['tipo'] == 'Egreso') | (df_filtrado['categoria'] == 'Préstamo / Crédito recibido')) & (df_filtrado['estado_deuda'] == 'Pendiente')]
        por_pagar = (df_pend_egr['monto'] - df_pend_egr['abono_acumulado']).sum() if not df_pend_egr.empty else 0.0

        st.markdown("###")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🟢 Ingresos Reales", f"$ {ingresos:,.2f}")
        m2.metric("🔴 Egresos Reales", f"$ {egresos:,.2f}")
        m3.metric("💰 Balance Neto", f"$ {balance_neto:,.2f}")
        m4.metric("📈 Por Cobrar", f"$ {por_cobrar:,.2f}")
        m5.metric("📉 Por Pagar", f"$ {por_pagar:,.2f}")

        st.markdown("---")
        tab_resumen, tab_abonos, tab_graficas = st.tabs(["📋 Registros", "💵 Abonos y Deudas", "📈 Gráficas"])
        
        with tab_resumen:
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                buscar_bal = st.text_input("🔍 Buscar en el historial:", key="bus_bal").strip()
            with col_t2:
                st.write("###")
                if not df_filtrado.empty:
                    html_profesional_finanzas = generar_reporte_finanzas_profesional(df_filtrado, periodo, lote_seleccionado, ingresos, egresos, balance_neto, por_cobrar, por_pagar)
                    st.download_button("📄 Reporte Docs", html_profesional_finanzas, f"Reporte_Finanzas_{periodo}.doc", "application/msword", use_container_width=True)

            df_bal_vista = df_filtrado.copy()
            if buscar_bal:
                df_bal_vista = df_bal_vista[df_bal_vista.astype(str).apply(lambda x: x.str.contains(buscar_bal, case=False)).any(axis=1)]
                
            if not df_bal_vista.empty:
                df_bal_vista['fecha'] = df_bal_vista['fecha'].dt.strftime('%Y-%m-%d')
                st.dataframe(df_bal_vista.style.apply(colorear_filas_finanzas, axis=1), use_container_width=True)
            else:
                st.info("Sin registros con el filtro aplicado.")

        with tab_abonos:
            st.markdown("##### 💳 Gestor de Abonos Parciales")
            df_cuentas_abono = df_finanzas[df_finanzas['estado_deuda'] == 'Pendiente'].copy()
            if not df_cuentas_abono.empty:
                df_cuentas_abono['saldo_restante'] = df_cuentas_abono['monto'] - df_cuentas_abono['abono_acumulado']
                df_cuentas_abono = df_cuentas_abono[df_cuentas_abono['saldo_restante'] > 0]

            if not df_cuentas_abono.empty:
                df_cuentas_abono['opcion_texto'] = df_cuentas_abono.apply(lambda x: f"[{x['id']}] {x['tipo'].upper()} | {x['concepto']} | Resta: ${x['saldo_restante']:,.2f}", axis=1)
                asig_sel_texto = st.selectbox("Selecciona deuda a abonar:", df_cuentas_abono['opcion_texto'].tolist())
                id_abono_sel = asig_sel_texto.split("]")[0].replace("[", "").strip()
                fila_abono = df_cuentas_abono[df_cuentas_abono['id'] == id_abono_sel].iloc[0]
                saldo_actual_pendiente = float(fila_abono['saldo_restante'])

                c_ab1, c_ab2 = st.columns(2)
                with c_ab1:
                    monto_abono = st.number_input("Monto a Abonar ($ MXN)", min_value=0.01, max_value=saldo_actual_pendiente, value=saldo_actual_pendiente)
                    metodo_pago_abono = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque"])
                with c_ab2:
                    fecha_abono = st.date_input("Fecha de Abono", datetime.today()).strftime('%Y-%m-%d')
                    concepto_abono = st.text_input("Nota del Abono", value=f"Abono a {fila_abono['concepto']}")

                if st.button("💳 Confirmar y Registrar Abono", type="primary", use_container_width=True):
                    nuevo_abono_acumulado = float(fila_abono['abono_acumulado']) + float(monto_abono)
                    nuevo_estado = "Pagado" if nuevo_abono_acumulado >= float(fila_abono['monto']) else "Pendiente"
                    
                    reg_padre = {
                        "id": fila_abono['id'], "fecha": str(fila_abono['fecha'])[:10],
                        "tipo": fila_abono['tipo'], "categoria": fila_abono['categoria'],
                        "concepto": fila_abono['concepto'], "monto": float(fila_abono['monto']),
                        "abono_acumulado": nuevo_abono_acumulado, "metodo_pago": fila_abono.get('metodo_pago', 'Efectivo'),
                        "asociado": fila_abono.get('asociado', ''), "empleado_responsable": fila_abono.get('empleado_responsable', ''),
                        "lote_asociado": fila_abono.get('lote_asociado', 'Ninguno'), "estado_deuda": nuevo_estado,
                        "fecha_vencimiento": str(fila_abono.get('fecha_vencimiento', ''))[:10]
                    }

                    reg_hijo = {
                        "id": f"AB-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}",
                        "fecha": fecha_abono, "tipo": "Egreso" if fila_abono['tipo'] == "Egreso" else "Ingreso",
                        "categoria": "Pago / Abono Préstamo" if "Préstamo" in str(fila_abono['categoria']) else fila_abono['categoria'],
                        "concepto": f"[ABONO] {concepto_abono} (Ref: {fila_abono['id']})",
                        "monto": float(monto_abono), "abono_acumulado": float(monto_abono),
                        "metodo_pago": metodo_pago_abono, "asociado": fila_abono.get('asociado', ''),
                        "empleado_responsable": fila_abono.get('empleado_responsable', ''),
                        "lote_asociado": fila_abono.get('lote_asociado', 'Ninguno'),
                        "estado_deuda": "Pagado", "id_origen_abono": fila_abono['id']
                    }

                    if guardar_registro("finanzas", reg_padre, "id") and guardar_registro("finanzas", reg_hijo, "id"):
                        st.success("Abono procesado correctamente.")
                        time.sleep(0.4)
                        st.rerun()
            else:
                st.info("Sin cuentas pendientes por abonar.")

        with tab_graficas:
            if not df_filtrado.empty:
                st.bar_chart(df_filtrado.groupby(['tipo', 'categoria'])['monto'].sum().unstack().fillna(0.0), use_container_width=True)

    st.markdown("---")
    st.markdown("### ➕ Registrar Nueva Transacción")
    f_tipo_dinamico = st.radio("Tipo:", ["Ingreso", "Egreso"], horizontal=True)
    
    with st.form("form_captura_finanzas"):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_fecha = st.date_input("Fecha", datetime.today()).strftime('%Y-%m-%d')
            opciones_cat = cat_ingresos if f_tipo_dinamico == "Ingreso" else cat_costos_directos + cat_gastos_operativos
            f_cat = st.selectbox("Categoría", opciones_cat)
            f_concepto = st.text_input("Concepto / Descripción").strip()

        with c2:
            f_monto = st.number_input("Monto ($ MXN)", min_value=0.0, step=50.0)
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            f_asociado = st.selectbox("Cliente/Proveedor", lista_clientes if f_tipo_dinamico == "Ingreso" else lista_proveedores)

        with c3:
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            f_emp = st.selectbox("Empleado Responsable", ["-- Selecciona --"] + lista_empleados)

        if st.form_submit_button("💾 Registrar Transacción", type="primary", use_container_width=True):
            if f_monto <= 0 or not f_concepto or f_emp == "-- Selecciona --":
                st.error("❌ Completa un concepto, monto válido y selecciona un empleado.")
            else:
                reg_nuevo = {
                    "id": f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}",
                    "fecha": f_fecha, "tipo": f_tipo_dinamico, "categoria": f_cat,
                    "concepto": f_concepto, "monto": float(f_monto), "abono_acumulado": 0.0,
                    "metodo_pago": f_pago, "asociado": f_asociado, "empleado_responsable": f_emp,
                    "lote_asociado": f_lote, "estado_deuda": f_estado,
                    "fecha_vencimiento": f_fecha
                }
                if guardar_registro("finanzas", reg_nuevo, "id"):
                    st.success("Transacción registrada correctamente.")
                    time.sleep(0.4)
                    st.rerun()

# ==========================================
# MÓDULO 2: EMPLEADOS
# ==========================================
elif modulo_activo == "🤠 Personal / Empleados":
    st.subheader("🤠 Personal y Empleados")
    tab_registro, tab_listado = st.tabs(["➕ Captura / Edición", "📋 Empleados"])

    with tab_registro:
        with st.form("form_emp"):
            c1, c2 = st.columns(2)
            with c1:
                e_nom = st.text_input("Nombre Completo *").strip().upper()
                e_pue = st.text_input("Puesto").strip().upper()
                e_sue = st.number_input("Sueldo ($ MXN)", min_value=0.0, step=100.0)
            with c2:
                e_tel = st.text_input("Teléfono").strip()
                e_ema = st.text_input("Correo Electrónico").strip().lower()
                e_est = st.selectbox("Estatus", ["Activo", "Inactivo"])

            if st.form_submit_button("💾 Guardar Empleado", type="primary", use_container_width=True):
                if not e_nom:
                    st.error("El nombre es requerido.")
                else:
                    d_emp = {"nombre": e_nom, "puesto_funcion": e_pue, "sueldo": e_sue, "telefono": e_tel, "email": e_ema, "estatus": e_est}
                    if guardar_registro("empleados", d_emp, "nombre"):
                        st.success("Empleado guardado.")
                        time.sleep(0.4)
                        st.rerun()

    with tab_listado:
        if not df_empleados.empty:
            st.dataframe(df_empleados, use_container_width=True, hide_index=True)

# ==========================================
# MÓDULO 3: CLIENTES
# ==========================================
elif modulo_activo == "🤝 Clientes":
    st.subheader("🤝 Módulo de Clientes")
    with st.form("form_cli"):
        c1, c2 = st.columns(2)
        with c1:
            c_nom = st.text_input("Nombre / Razón Social *").strip().upper()
            c_tel = st.text_input("Teléfono").strip()
        with c2:
            c_ema = st.text_input("Correo").strip().lower()
            c_dir = st.text_input("Ubicación").strip()
            
        if st.form_submit_button("💾 Guardar Cliente", type="primary", use_container_width=True):
            if not c_nom:
                st.error("Nombre requerido.")
            else:
                if guardar_registro("clientes", {"nombre_razon": c_nom, "telefono": c_tel, "email": c_ema, "direccion": c_dir}, "nombre_razon"):
                    st.success("Cliente guardado.")
                    time.sleep(0.4)
                    st.rerun()

    if not df_clientes.empty:
        st.dataframe(df_clientes, use_container_width=True, hide_index=True)

# ==========================================
# MÓDULO 4: PROVEEDORES
# ==========================================
elif modulo_activo == "🚜 Proveedores":
    st.subheader("🚜 Control de Proveedores")
    with st.form("form_prov"):
        c1, c2 = st.columns(2)
        with c1:
            p_nom = st.text_input("Proveedor / Razón Social *").strip().upper()
            p_ins = st.text_input("Insumo Principal *").strip().upper()
            p_tel = st.text_input("Teléfono").strip()
        with c2:
            p_dir = st.text_input("Dirección").strip().upper()
            p_crd = st.number_input("Días de Crédito", min_value=0, max_value=120)
            p_est = st.selectbox("Estatus", ["ACTIVO", "INACTIVO"])

        if st.form_submit_button("💾 Guardar Proveedor", type="primary", use_container_width=True):
            if not p_nom or not p_ins:
                st.error("Nombre e insumo requeridos.")
            else:
                d_p = {"nombre_proveedor": p_nom, "insumo_principal": p_ins, "telefono": p_tel, "direccion": p_dir, "dias_credito": p_crd, "estatus": p_est}
                if guardar_registro("proveedores", d_p, "nombre_proveedor"):
                    st.success("Proveedor registrado.")
                    time.sleep(0.4)
                    st.rerun()

    if not df_proveedores.empty:
        st.dataframe(df_proveedores, use_container_width=True, hide_index=True)

# ==========================================
# MÓDULO 5: CONTROL DE LOTES
# ==========================================
elif modulo_activo == "🐂 Control de Lotes":
    st.subheader("🐂 Control de Lotes de Ganado")
    
    tab_l1, tab_l2, tab_l3 = st.tabs(["➕ Registro Lote", "📋 Catálogo Lotes", "💰 Finanzas por Lote"])

    with tab_l1:
        with st.form("form_lotes_moderno"):
            c1, c2 = st.columns(2)
            with c1:
                l_nom = st.text_input("Nombre / Código de Lote *").strip().upper()
                l_raz = st.selectbox("Raza / Propósito", ["Sardo Negro", "Suiz-Bu", "Comercial / Engorda", "Mestizo / Varios"])
                l_cab = st.number_input("Cabezas", min_value=1, value=1)
            with c2:
                l_pes = st.number_input("Peso Promedio (kg)", min_value=0.0, step=5.0)
                l_est = st.selectbox("Estado", ["Activo", "Vendido / Cerrado"])
                l_obs = st.text_area("Notas / Ubicación", height=70).strip()

            if st.form_submit_button("💾 Guardar Lote", type="primary", use_container_width=True):
                if not l_nom:
                    st.error("Nombre de lote requerido.")
                else:
                    d_lote = {
                        "nombre_lote": l_nom, "raza_tipo": l_raz, "num_cabezas": l_cab,
                        "fecha_ingreso": datetime.today().strftime('%Y-%m-%d'),
                        "peso_promedio": l_pes, "estatus": l_est, "observaciones": l_obs
                    }
                    if guardar_registro("lotes", d_lote, "nombre_lote"):
                        st.success("Lote registrado correctamente.")
                        time.sleep(0.4)
                        st.rerun()

    with tab_l2:
        if not df_lotes.empty:
            st.dataframe(df_lotes, use_container_width=True, hide_index=True)
            st.divider()
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                l_del = st.selectbox("Lote a eliminar:", df_lotes['nombre_lote'].unique())
            with col_d2:
                st.write("###")
                if st.button("🗑️ Eliminar Lote", type="primary", use_container_width=True):
                    if eliminar_registro("lotes", "nombre_lote", l_del):
                        st.success("Lote eliminado.")
                        time.sleep(0.4)
                        st.rerun()

    with tab_l3:
        if not df_lotes.empty and not df_finanzas.empty:
            l_sel = st.selectbox("Selecciona lote para auditoría:", df_lotes['nombre_lote'].unique())
            df_fl = df_finanzas[df_finanzas['lote_asociado'] == l_sel]
            if not df_fl.empty:
                st.dataframe(df_fl[['fecha', 'tipo', 'categoria', 'concepto', 'monto', 'estado_deuda']], use_container_width=True)
            else:
                st.info("Sin registros financieros asociados a este lote.")
