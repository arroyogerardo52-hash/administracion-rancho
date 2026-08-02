import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import time
import json
import os

# -------------------------------------------------------------
# 1. BANDERAS DE PRIVACIDAD Y CARGA DE USUARIOS
# -------------------------------------------------------------
TIEMPO_EXPIRED = 300  # Tiempo en segundos para cerrar sesión (5 min)

# Cargar usuarios desde Streamlit Secrets (Nube) o fallback por defecto
if "usuarios" in st.secrets:
    # Lee los usuarios configurados en los Secrets de Streamlit Cloud
    USUARIOS = {str(k).strip().lower(): str(v).strip() for k, v in st.secrets["usuarios"].items()}
else:
    # Usuario administrador por defecto en local
    # (Usuario: gerardo | Contraseña: ADMINpg120214)
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
# 2. PUERTA DE ENTRADA (PANTALLA DE LOGIN CON COMPATIBILIDAD MÓVIL)
# -------------------------------------------------------------
if not st.session_state.autenticado:
    st.title("🔒 Inicia sesión para continuar")
    
    usuario_ingresado = st.text_input("Usuario")
    clave_ingresada = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar", use_container_width=True):
        # .strip() elimina espacios invisibles del teclado móvil
        # .lower() convierte a minúsculas para ignorar mayúsculas automáticas
        usr_limpio = usuario_ingresado.strip().lower()
        pwd_limpia = clave_ingresada.strip()

        # Validación flexible
        if usr_limpio in USUARIOS and USUARIOS[usr_limpio] == pwd_limpia:
            st.session_state.autenticado = True
            st.session_state.usuario_actual = usr_limpio
            st.success("¡Bienvenido!")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
            
    # Bloquea la app: nada debajo de esta línea se muestra sin sesión activa
    st.stop()

# -------------------------------------------------------------
# 3. BARRA LATERAL (Solo visible si ya inició sesión)
# -------------------------------------------------------------
with st.sidebar:
    st.write(f"👤 Hola, **{st.session_state.usuario_actual.capitalize()}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        cerrar_sesion()

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

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

# ==========================================
# BARRA LATERAL: NAVEGACIÓN Y RESPALDOS
# ==========================================
with st.sidebar:
    # MENÚ DE NAVEGACIÓN PRINCIPAL
    st.header("🧭 Menú Principal")
    modulo_activo = st.radio(
        "Ir a la sección:",
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
            st.error(f"Error al generar el respaldo: {e}")

# ENCABEZADO PRINCIPAL DE LA PÁGINA
st.title("Rancho AE: Sistema de Administración")

st.markdown("---")

# ==========================================
# FUNCIONES AUXILIARES Y DE REPORTES HTML
# ==========================================
from datetime import datetime, timedelta
import time
import pandas as pd
import pytz
import streamlit as st

def colorear_filas_finanzas(row):
    if row['tipo'] == 'Ingreso':
        return ['background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; font-weight: bold;'] * len(row)
    elif row['tipo'] == 'Egreso':
        return ['background-color: rgba(231, 76, 60, 0.12); color: #e74c3c;'] * len(row)
    return [''] * len(row)

def obtener_fecha_hora_mx():
    """Obtiene la fecha y hora actual configurada en la zona horaria de México."""
    zona_mx = pytz.timezone('America/Mexico_City')
    return datetime.now(zona_mx).strftime('%d/%m/%Y %I:%M %p')

def clasificar_categoria(cat):
    """Clasifica una categoría contable en su respectivo tipo y rubro de costo/gasto."""
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
            <thead>
                <tr>
    """
    for header in columnas_headers:
        html += f"<th>{header}</th>"
    html += """
                </tr>
            </thead>
            <tbody>
    """
    for _, fila in df_datos.iterrows():
        html += "<tr>"
        for col_bd in mapping_columnas:
            val = fila.get(col_bd, '')
            if pd.isnull(val):
                val = ''
            elif isinstance(val, datetime) or hasattr(val, 'strftime'):
                val = val.strftime('%Y-%m-%d')
            elif isinstance(val, (int, float)) and col_bd == 'monto':
                val = f"${val:,.2f}"
            html += f"<td>{val}</td>"
        html += "</tr>"
        
    html += """
            </tbody>
        </table>
        <p style='margin-top:40px; font-size:11px; color:#999; text-align: center; border-top: 1px dashed #ccc; padding-top: 10px;'>Documento administrativo confidencial generado por el Sistema de Control Interno Rancho AE.</p>
    </body>
    </html>
    """
    return html

def generar_reporte_finanzas_profesional(df_datos, periodo, lote, ing, egr, net, cob, pag):
    hoy_str = obtener_fecha_hora_mx()
    
    # --- CÁLCULO DINÁMICO DE ESTADO DE RESULTADOS (P&L) ---
    df_pagados = df_datos[df_datos['estado_deuda'] == 'Pagado'].copy() if not df_datos.empty else pd.DataFrame()
    
    tot_ingresos = ing
    tot_costos_directos = 0.0
    tot_gastos_operativos = 0.0
    tot_otros = 0.0
    
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
        <title>Reporte Financiero Rancho AE</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2C3E50; margin: 25px; }}
            .header-title {{ font-size: 24pt; color: #1A365D; font-weight: bold; margin: 0; }}
            .header-subtitle {{ font-size: 11pt; color: #718096; text-transform: uppercase; font-weight: bold; }}
            .divider {{ height: 3px; background-color: #2B6CB0; margin-top: 5px; margin-bottom: 20px; }}
            
            .meta-section {{ background-color: #EDF2F7; padding: 12px; border-radius: 5px; margin-bottom: 20px; font-size: 10pt; }}
            .meta-table {{ width: 100%; border-collapse: collapse; }}
            .meta-table td {{ padding: 4px 0; color: #4A5568; border: none; }}
            
            .kpi-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            .kpi-card {{ background: #F8FAFC; border: 1px solid #CBD5E0; padding: 10px; text-align: center; border-top: 4px solid #2B6CB0; }}
            .kpi-title {{ font-size: 9pt; text-transform: uppercase; color: #718096; font-weight: bold; }}
            .kpi-value {{ font-size: 12pt; font-weight: bold; color: #1A365D; margin-top: 4px; }}
            
            .section-title {{ font-size: 13pt; color: #1A365D; margin-top: 25px; margin-bottom: 10px; font-weight: bold; border-bottom: 2px solid #E2E8F0; padding-bottom: 4px; }}
            
            .pnl-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 10pt; }}
            .pnl-table td {{ padding: 8px; border-bottom: 1px solid #E2E8F0; border-top: none; border-left: none; border-right: none; }}
            
            .data-table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 9pt; }}
            .data-table th {{ background-color: #1A365D; color: white; padding: 8px; text-align: left; font-weight: bold; text-transform: uppercase; border: 1px solid #1A365D; }}
            .data-table td {{ border: 1px solid #CBD5E0; padding: 6px 8px; color: #2D3748; }}
            .data-table tr:nth-child(even) {{ background-color: #F7FAFC; }}
            
            .text-right {{ text-align: right; }}
            .bold {{ font-weight: bold; }}
            .color-ingreso {{ color: #27AE60; }}
            .color-egreso {{ color: #C0392B; }}
        </style>
    </head>
    <body>
        <!-- ENCABEZADO INSTITUCIONAL -->
        <div class="header-title">RANCHO AE</div>
        <div class="header-subtitle">Informe Ejecutivo de Control Financiero y Estado de Resultados</div>
        <div class="divider"></div>
        
        <!-- METADATOS DEL REPORTE -->
        <div class="meta-section">
            <table class="meta-table">
                <tr>
                    <td width="20%"><strong>Período Auditado:</strong></td><td width="30%">{periodo}</td>
                    <td width="20%"><strong>Filtro de Lote:</strong></td><td width="30%">{lote}</td>
                </tr>
                <tr>
                    <td><strong>Fecha de Emisión:</strong></td><td>{hoy_str}</td>
                    <td><strong>Estatus Financiero:</strong></td><td>Cierre Operativo Auditado</td>
                </tr>
            </table>
        </div>
        
        <!-- RESUMEN DE INDICADORES (KPIs) -->
        <div class="section-title">1. Resumen de Flujo de Efectivo</div>
        <table class="kpi-table">
            <tr>
                <td class="kpi-card" style="border-top-color: #2ECC71;" width="20%">
                    <div class="kpi-title">Ingresos Reales</div>
                    <div class="kpi-value color-ingreso">${ing:,.2f}</div>
                </td>
                <td class="kpi-card" style="border-top-color: #E74C3C;" width="20%">
                    <div class="kpi-title">Egresos Reales</div>
                    <div class="kpi-value color-egreso">${egr:,.2f}</div>
                </td>
                <td class="kpi-card" style="border-top-color: #2B6CB0;" width="20%">
                    <div class="kpi-title">Balance Neto</div>
                    <div class="kpi-value">${net:,.2f}</div>
                </td>
                <td class="kpi-card" style="border-top-color: #3182CE;" width="20%">
                    <div class="kpi-title">Por Cobrar</div>
                    <div class="kpi-value" style="color:#2B6CB0;">${cob:,.2f}</div>
                </td>
                <td class="kpi-card" style="border-top-color: #DD6B20;" width="20%">
                    <div class="kpi-title">Por Pagar</div>
                    <div class="kpi-value" style="color:#D69E2E;">${pag:,.2f}</div>
                </td>
            </tr>
        </table>
        
        <!-- ESTADO DE RESULTADOS (P&L) -->
        <div class="section-title">2. Estado de Resultados y Rentabilidad (P&L)</div>
        <table class="pnl-table">
            <tr style="background-color: #F0FFF4; font-weight: bold;">
                <td>(+) INGRESOS TOTALES (COBRADOS)</td>
                <td class="text-right color-ingreso">${tot_ingresos:,.2f} MXN</td>
            </tr>
            <tr>
                <td style="padding-left: 20px;">(-) Costos Directos (Ganado, Alimento, Medicina, Veterinario)</td>
                <td class="text-right color-egreso">-${tot_costos_directos:,.2f} MXN</td>
            </tr>
            <tr style="background-color: #EBF8FF; font-weight: bold;">
                <td>(=) UTILIDAD BRUTA (Margen Bruto: {margen_bruto:.1f}%)</td>
                <td class="text-right" style="color: #2B6CB0;">${utilidad_bruta:,.2f} MXN</td>
            </tr>
            <tr>
                <td style="padding-left: 20px;">(-) Gastos Operativos (Nómina, Oficina, Mantenimiento, Combustible)</td>
                <td class="text-right color-egreso">-${tot_gastos_operativos:,.2f} MXN</td>
            </tr>
            <tr>
                <td style="padding-left: 20px;">(-) Otros Gastos Generalizados</td>
                <td class="text-right color-egreso">-${tot_otros:,.2f} MXN</td>
            </tr>
            <tr style="background-color: #1A365D; color: white; font-weight: bold;">
                <td style="padding: 10px;">(=) UTILIDAD NETA REAL (Margen Neto: {margen_neto:.1f}%)</td>
                <td class="text-right" style="padding: 10px; font-size: 11pt;">${utilidad_neta:,.2f} MXN</td>
            </tr>
        </table>
        
        <!-- DESGLOSE DETALLADO DE TRANSACCIONES -->
        <div class="section-title">3. Registro Detallado de Transacciones ({len(df_datos)} movimientos)</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Categoría</th>
                    <th>Concepto / Descripción</th>
                    <th>Lote</th>
                    <th>Método</th>
                    <th>Estado</th>
                    <th class="text-right">Monto (MXN)</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, fila in df_datos.iterrows():
        f_date = fila.get('fecha', '')
        f_str = f_date.strftime('%Y-%m-%d') if hasattr(f_date, 'strftime') else str(f_date)[:10]
        
        tipo_mov = fila.get('tipo', '')
        clase_color = "color-ingreso bold" if tipo_mov == "Ingreso" else "color-egreso"
        
        html += f"""
                <tr>
                    <td>{f_str}</td>
                    <td class="{clase_color}">{tipo_mov}</td>
                    <td>{fila.get('categoria', 'General')}</td>
                    <td>{fila.get('concepto', '-')}</td>
                    <td>{fila.get('lote_asociado', 'Ninguno')}</td>
                    <td>{fila.get('metodo_pago', '-')}</td>
                    <td>{fila.get('estado_deuda', 'Pagado')}</td>
                    <td class="text-right bold {clase_color}">${fila.get('monto', 0.0):,.2f}</td>
                </tr>
        """
        
    color_bal_final = '#27AE60' if net >= 0 else '#C0392B'
    html += f"""
                <tr style="background-color: #EDF2F7; font-weight: bold;">
                    <td colspan="7" class="text-right" style="padding: 10px;">BALANCE GENERAL DEL PERÍODO EXPORTADO:</td>
                    <td class="text-right" style="padding: 10px; color: {color_bal_final}; font-size: 11pt;">${net:,.2f} MXN</td>
                </tr>
            </tbody>
        </table>
        
        <br><br>
        <p style='font-size:9pt; color:#A0AEC0; text-align: center; border-top: 1px dashed #CBD5E0; padding-top: 10px;'>
            Este balance ejecutivo constituye un extracto oficial de la contabilidad interna de Rancho AE. Súbase directamente a Google Drive para su archivo permanente o firmas conducentes.
        </p>
    </body>
    </html>
    """
    return html

# ==========================================
# RENDERIZADO CONDICIONAL DE MÓDULOS
# ==========================================

# ==========================================
# MÓDULO 1: DASHBOARD Y FINANZAS
# ==========================================
if modulo_activo == "📊 Dashboard & Finanzas":
    st.header("📊 Balance y Control General Financiero")

    # --- INYECCIÓN DE CSS PARA EVITAR TRUNCAMIENTO EN METRICAS (PUNTOS SUSPENSIVOS) ---
    st.markdown("""
        <style>
        div[data-testid="stMetricValue"] {
            font-size: calc(1rem + 0.6vw) !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        .stCardPos {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #e0e0e0;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- DEFINICIÓN DE CATEGORÍAS PARA EL ESTADO DE RESULTADOS ---
    cat_ingresos = ["Venta de ganado", "Varios (Ingresos)"]
    cat_costos_directos = ["Compra de ganado", "Alimentos", "Medicamentos", "Servicios veterinarios", "Dosis de semen", "Varios (Costos directos)"]
    cat_gastos_operativos = ["Gastos de oficina", "Arriendo", "Nomina", "Combustible", "Mantenimiento", "Varios (Gastos operativos)"]
    todas_las_categorias = cat_ingresos + cat_costos_directos + cat_gastos_operativos

    # --- EXTRACCIÓN DE LISTAS PARA SELECTBOXES (CON FALLBACKS DE SEGURIDAD) ---
    lista_clientes = ["Público en general"]
    if 'df_clientes' in locals() and not df_clientes.empty:
        col_c = 'nombre' if 'nombre' in df_clientes.columns else df_clientes.columns[0]
        lista_clientes += [c for c in df_clientes[col_c].dropna().unique() if c != "Público en general"]

    lista_proveedores = ["Egreso general"]
    if 'df_proveedores' in locals() and not df_proveedores.empty:
        col_p = 'nombre' if 'nombre' in df_proveedores.columns else df_proveedores.columns[0]
        lista_proveedores += [p for p in df_proveedores[col_p].dropna().unique() if p != "Egreso general"]

    lista_empleados = []
    if 'df_empleados' in locals() and not df_empleados.empty:
        col_e = 'nombre' if 'nombre' in df_empleados.columns else df_empleados.columns[0]
        lista_empleados = list(df_empleados[col_e].dropna().unique())
    else:
        lista_empleados = ["Empleado General / Caja"]

    def clasificar_categoria(cat):
        if cat in cat_ingresos: return "Ingreso", "Ingreso"
        elif cat in cat_costos_directos: return "Egreso", "Costo Directo"
        elif cat in cat_gastos_operativos: return "Egreso", "Gasto Operativo"
        else: return "Egreso", "Otros" # Por seguridad en registros viejos

    if not df_finanzas.empty:
        df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
        df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
        if 'fecha_vencimiento' in df_finanzas.columns:
            df_finanzas['fecha_vencimiento'] = pd.to_datetime(df_finanzas['fecha_vencimiento'], errors='coerce')
        df_finanzas = df_finanzas.dropna(subset=['fecha'])
        
        # --- 🔔 SISTEMA DE ALERTAS Y RECORDATORIOS DE VENCIMIENTO ---
        hoy_dt = datetime.today()
        df_pendientes = df_finanzas[df_finanzas['estado_deuda'] == 'Pendiente'].copy()
        
        if not df_pendientes.empty and 'fecha_vencimiento' in df_pendientes.columns:
            df_vencidos = df_pendientes[df_pendientes['fecha_vencimiento'] < hoy_dt]
            df_por_vencer = df_pendientes[(df_pendientes['fecha_vencimiento'] >= hoy_dt) & (df_pendientes['fecha_vencimiento'] <= hoy_dt + timedelta(days=7))]
            
            if not df_vencidos.empty or not df_por_vencer.empty:
                with st.expander("🔔 **Alertas de Cuentas Pendientes y Vencimientos**", expanded=True):
                    col_al1, col_al2 = st.columns(2)
                    with col_al1:
                        if not df_vencidos.empty:
                            tot_vencido = df_vencidos['monto'].sum()
                            st.error(f"⚠️ **{len(df_vencidos)} cuentas vencidas** por un total de **$ {tot_vencido:,.2f} MXN**.")
                            st.dataframe(df_vencidos[['fecha_vencimiento', 'concepto', 'tipo', 'monto', 'lote_asociado']], use_container_width=True)
                    with col_al2:
                        if not df_por_vencer.empty:
                            tot_por_vencer = df_por_vencer['monto'].sum()
                            st.warning(f"⏳ **{len(df_por_vencer)} cuentas por vencer** en los próximos 7 días ($ {tot_por_vencer:,.2f} MXN).")
                            st.dataframe(df_por_vencer[['fecha_vencimiento', 'concepto', 'tipo', 'monto', 'lote_asociado']], use_container_width=True)

        st.subheader("📆 Filtros de Consulta")
        col_filtro, col_lote_filtro, col_estado_filtro, col_fechas = st.columns([2, 2, 2, 3])
        
        fecha_inicio = hoy_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = hoy_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        with col_filtro:
            periodo = st.selectbox(
                "Período:",
                ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"]
            )

        with col_lote_filtro:
            opciones_filtro_lote = ["Todos los Lotes"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_filtro_lote += list(df_lotes['nombre_lote'].dropna().unique())
            lote_seleccionado = st.selectbox("Lote Asociado:", opciones_filtro_lote)

        with col_estado_filtro:
            filtro_estado = st.selectbox("Estado de Pago:", ["Todos", "Pagado", "Pendiente"])

        with col_fechas:
            if periodo == "Esta Semana":
                lunes = hoy_dt - timedelta(days=hoy_dt.weekday())
                fecha_inicio = lunes.replace(hour=0, minute=0, second=0, microsecond=0)
                fecha_fin = (lunes + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
                st.info(f"Del: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
                
            elif periodo == "Este Mes":
                fecha_inicio = hoy_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                next_month = hoy_dt.replace(day=28) + timedelta(days=4)
                ultimo_dia = next_month - timedelta(days=next_month.day)
                fecha_fin = ultimo_dia.replace(hour=23, minute=59, second=59, microsecond=999999)
                st.info(f"Mostrando: **{fecha_inicio.strftime('%B %Y')}**")
                
            elif periodo == "Este Año":
                fecha_inicio = hoy_dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                fecha_fin = hoy_dt.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
                st.info(f"Año: **{hoy_dt.year}**")
                
            elif periodo == "Rango Personalizado":
                fecha_defecto_inicio = (hoy_dt - timedelta(days=30)).date()
                fecha_defecto_fin = hoy_dt.date()
                rango_fechas = st.date_input("Rango de fechas:", [fecha_defecto_inicio, fecha_defecto_fin])
                if isinstance(rango_fechas, (list, tuple)):
                    if len(rango_fechas) == 2:
                        fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                        fecha_fin = datetime.combine(rango_fechas[1], datetime.max.time())
                    else:
                        fecha_inicio, fecha_fin = None, None

        df_filtrado = df_finanzas.copy()
        try:
            if df_filtrado['fecha'].dt.tz is not None:
                df_filtrado['fecha'] = df_filtrado['fecha'].dt.tz_localize(None)
        except AttributeError: pass

        if periodo != "Todo el Historial" and fecha_inicio is not None and fecha_fin is not None:
            df_filtrado = df_filtrado[(df_filtrado['fecha'] >= pd.to_datetime(fecha_inicio)) & (df_filtrado['fecha'] <= pd.to_datetime(fecha_fin))]

        if lote_seleccionado != "Todos los Lotes" and 'lote_asociado' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['lote_asociado'] == lote_seleccionado]

        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['estado_deuda'] == filtro_estado]

        ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
        egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
        balance_neto = ingresos - egresos
        
        por_cobrar = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
        por_pagar = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
        
        # --- CREACIÓN DE PESTAÑAS ---
        tab_resumen, tab_graficas, tab_rentabilidad = st.tabs(["📋 Resumen Numérico", "📈 Análisis Gráfico", "📊 Estados Financieros y Rentabilidad"])
        
        with tab_resumen:
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("🟢 Ingresos Reales", f"$ {ingresos:,.2f} MXN")
            m2.metric("🔴 Egresos Reales", f"$ {egresos:,.2f} MXN")
            m3.metric("💰 Balance Neto", f"$ {balance_neto:,.2f} MXN")
            m4.metric("📈 Por Cobrar", f"$ {por_cobrar:,.2f} MXN")
            m5.metric("📉 Por Pagar", f"$ {por_pagar:,.2f} MXN")
            
            st.write("---")
            col_tit_trans, col_btn_rep_filtrado = st.columns([3, 1])
            with col_tit_trans:
                st.subheader("📋 Transacciones del Período Seleccionado")
            with col_btn_rep_filtrado:
                if not df_filtrado.empty:
                    html_profesional_finanzas = generar_reporte_finanzas_profesional(
                        df_filtrado, periodo, lote_seleccionado, ingresos, egresos, balance_neto, por_cobrar, por_pagar
                    )
                    st.download_button(
                        label="📄 Exportar Reporte (Docs)",
                        data=html_profesional_finanzas,
                        file_name=f"Reporte_Finanzas_{periodo.replace(' ', '_')}.doc",
                        mime="application/msword",
                        use_container_width=True
                    )
            
            buscar_bal = st.text_input("🔍 Buscar en las transacciones del período:", key="bus_bal").strip()
            df_bal_vista = df_filtrado.copy()
            
            if buscar_bal:
                df_bal_vista = df_bal_vista[df_bal_vista.astype(str).apply(lambda x: x.str.contains(buscar_bal, case=False)).any(axis=1)]
                
            if not df_bal_vista.empty:
                df_bal_vista['fecha'] = df_bal_vista['fecha'].dt.strftime('%Y-%m-%d')
                df_bal_estilizado = (df_bal_vista.style
                                     .apply(colorear_filas_finanzas, axis=1)
                                     .format({'monto': '$ {:,.2f} MXN'}))
                st.dataframe(df_bal_estilizado, use_container_width=True)
            else:
                st.info("No hay registros que coincidan con la búsqueda.")

        with tab_graficas:
            st.subheader("📊 Visualización de Rendimiento")
            if not df_filtrado.empty:
                cg1, cg2 = st.columns(2)
                with cg1:
                    st.write("### 💰 Ingresos vs Egresos Reales (MXN)")
                    df_pie = df_filtrado[df_filtrado['estado_deuda'] == 'Pagado'].groupby('tipo')['monto'].sum().reset_index()
                    if not df_pie.empty:
                        st.bar_chart(data=df_pie, x='tipo', y='monto', color='tipo', use_container_width=True)
                with cg2:
                    st.write("### 📌 Flujo por Categoría (MXN)")
                    col_cat = 'categoria' if 'categoria' in df_filtrado.columns else 'tipo'
                    df_cat = df_filtrado.groupby([col_cat, 'tipo'])['monto'].sum().unstack().fillna(0.0)
                    st.bar_chart(df_cat, use_container_width=True)
                st.write("### 📈 Tendencia Financiera Histórica (MXN)")
                df_linea = df_filtrado.copy()
                df_linea['Fecha'] = df_linea['fecha'].dt.date
                df_tendencia = df_linea.groupby(['Fecha', 'tipo'])['monto'].sum().unstack().fillna(0.0)
                if 'Ingreso' not in df_tendencia.columns: df_tendencia['Ingreso'] = 0.0
                if 'Egreso' not in df_tendencia.columns: df_tendencia['Egreso'] = 0.0
                st.line_chart(df_tendencia[['Ingreso', 'Egreso']], use_container_width=True)
            else:
                st.info("No hay datos para graficar.")

        with tab_rentabilidad:
            st.subheader("📊 Estado de Resultados (P&L) y Rentabilidad")
            st.markdown("Cálculos expresados en **Pesos Mexicanos (MXN)** basados **exclusivamente en transacciones pagadas/cobradas** dentro del período.")
            
            df_pagados = df_filtrado[df_filtrado['estado_deuda'] == 'Pagado'].copy()
            if not df_pagados.empty:
                df_pagados['Rubro'] = df_pagados['categoria'].apply(lambda x: clasificar_categoria(x)[1])
                
                tot_ingresos = df_pagados[df_pagados['Rubro'] == 'Ingreso']['monto'].sum()
                tot_costos_directos = df_pagados[df_pagados['Rubro'] == 'Costo Directo']['monto'].sum()
                tot_gastos_operativos = df_pagados[df_pagados['Rubro'] == 'Gasto Operativo']['monto'].sum()
                tot_otros = df_pagados[df_pagados['Rubro'] == 'Otros']['monto'].sum()
                
                utilidad_bruta = tot_ingresos - tot_costos_directos
                margen_bruto = (utilidad_bruta / tot_ingresos * 100) if tot_ingresos > 0 else 0.0
                
                utilidad_neta = utilidad_bruta - tot_gastos_operativos - tot_otros
                margen_neto = (utilidad_neta / tot_ingresos * 100) if tot_ingresos > 0 else 0.0
                
                flujo_caja = tot_ingresos - (tot_costos_directos + tot_gastos_operativos + tot_otros)
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("1️⃣ Flujo de Caja Total", f"$ {flujo_caja:,.2f} MXN", help="Efectivo real disponible")
                k2.metric("2️⃣ Utilidad Bruta", f"$ {utilidad_bruta:,.2f} MXN", help="Ingresos menos Costos Directos")
                k3.metric("3️⃣ Margen Bruto (%)", f"{margen_bruto:.1f}%")
                k4.metric("4️⃣ Rentabilidad (Margen Neto)", f"{margen_neto:.1f}%")
                
                st.write("---")
                
                if 'lote_asociado' in df_pagados.columns:
                    st.markdown("### 🐄 Costos y Rentabilidad por Lote Registrado")
                    df_lotes_val = df_pagados[df_pagados['lote_asociado'] != 'Ninguno']
                    
                    if not df_lotes_val.empty:
                        df_lotes_pnl = df_lotes_val.groupby(['lote_asociado', 'tipo'])['monto'].sum().unstack().fillna(0.0)
                        
                        if 'Ingreso' not in df_lotes_pnl.columns: df_lotes_pnl['Ingreso'] = 0.0
                        if 'Egreso' not in df_lotes_pnl.columns: df_lotes_pnl['Egreso'] = 0.0
                        
                        df_lotes_pnl['Balance Lote (MXN)'] = df_lotes_pnl['Ingreso'] - df_lotes_pnl['Egreso']
                        
                        df_lotes_pnl = df_lotes_pnl[['Ingreso', 'Egreso', 'Balance Lote (MXN)']]
                        df_lotes_pnl.columns = ['Ingresos Totales', 'Egresos Totales', 'Balance Lote (MXN)']
                        
                        st.dataframe(df_lotes_pnl.style.format("$ {:,.2f} MXN"), use_container_width=True)
                    else:
                        st.info("No hay transacciones pagadas vinculadas a un lote específico en este período.")
                
                st.markdown("### 📑 Desglose General de Estado de Resultados (MXN)")
                
                color_neta = '#4CAF50' if utilidad_neta >= 0 else '#f44336'
                html_pnl = f"""
                <div style="background-color:#1e1e1e; padding:20px; border-radius:10px; color:white; font-family:sans-serif;">
                    <table style="width:100%; border-collapse:collapse; font-size:16px;">
                        <tr style="border-bottom: 2px solid #4CAF50;">
                            <td style="padding:10px; font-weight:bold;">(+) INGRESOS TOTALES</td>
                            <td style="padding:10px; text-align:right; font-weight:bold; color:#4CAF50;">$ {tot_ingresos:,.2f} MXN</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #555;">
                            <td style="padding:10px; padding-left:30px;">(-) Costos Directos (Ganado, Alimento, Salud)</td>
                            <td style="padding:10px; text-align:right; color:#ff9800;">-$ {tot_costos_directos:,.2f} MXN</td>
                        </tr>
                        <tr style="border-bottom: 2px solid #2196F3; background-color:#2a2a2a;">
                            <td style="padding:10px; font-weight:bold;">(=) UTILIDAD BRUTA</td>
                            <td style="padding:10px; text-align:right; font-weight:bold; color:#2196F3;">$ {utilidad_bruta:,.2f} MXN</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #555;">
                            <td style="padding:10px; padding-left:30px;">(-) Gastos Operativos (Nómina, Oficina, Mantenimiento)</td>
                            <td style="padding:10px; text-align:right; color:#f44336;">-$ {tot_gastos_operativos:,.2f} MXN</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #555;">
                            <td style="padding:10px; padding-left:30px;">(-) Otros Gastos No Clasificados</td>
                            <td style="padding:10px; text-align:right; color:#f44336;">-$ {tot_otros:,.2f} MXN</td>
                        </tr>
                        <tr style="background-color:#000000;">
                            <td style="padding:15px; font-weight:bold; font-size:18px;">(=) UTILIDAD NETA (Ganancia Real)</td>
                            <td style="padding:15px; text-align:right; font-weight:bold; font-size:18px; color:{color_neta};">$ {utilidad_neta:,.2f} MXN</td>
                        </tr>
                    </table>
                </div>
                """
                st.markdown(html_pnl, unsafe_allow_html=True)
            else:
                st.info("No hay transacciones pagadas registradas en este período para calcular la rentabilidad.")

    else:
        st.warning("No se encontraron registros financieros para procesar en el sistema.")

    st.markdown("---")
    
    # --- FORMULARIO DE REGISTRO REESTRUCTURADO Y OPTIMIZADO ---
    st.subheader("💳 Captura y Registro Financiero")
    
    f_tipo_dinamico = st.radio("Tipo de Movimiento:", ["Ingreso", "Egreso"], horizontal=True)
    
    # Renderizado estético y limpio en un contenedor tipo tarjeta
    with st.container():
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            f_fecha = st.date_input("Fecha Transacción", datetime.today(), key="f_fec_pos").strftime('%Y-%m-%d')
            
            if f_tipo_dinamico == "Ingreso":
                opciones_categorias = cat_ingresos
            else:
                opciones_categorias = cat_costos_directos + cat_gastos_operativos
                
            f_cat = st.selectbox("Categoría", opciones_categorias, key="f_cat_pos")
            f_concepto = st.text_input("Concepto / Descripción", key="f_con_pos").strip()

        with col_f2:
            f_monto = st.number_input("Monto Total ($ MXN)", min_value=0.0, step=50.0, key="f_mon_pos")
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"], key="f_pag_pos")
            
            # --- ASIGNACIÓN DINÁMICA DE TERCEROS (CLIENTE / PROVEEDOR / EMPLEADO NÓMINA) ---
            if f_tipo_dinamico == "Ingreso":
                f_asociado = st.selectbox("Cliente Asociado", lista_clientes, index=0, key="f_cli_pos")
                etiqueta_asociado = "Cliente"
            else:
                if f_cat == "Nomina":
                    if lista_empleados:
                        f_asociado = st.selectbox("Empleado Beneficiario (Nómina)", lista_empleados, index=0, key="f_emp_nom_pos")
                    else:
                        f_asociado = st.text_input("Empleado Beneficiario", "Empleado General", key="f_emp_nom_txt")
                    etiqueta_asociado = "Empleado Beneficiario"
                else:
                    f_asociado = st.selectbox("Proveedor Asociado", lista_proveedores, index=0, key="f_prov_pos")
                    etiqueta_asociado = "Proveedor"

        with col_f3:
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes, key="f_lot_pos")
            
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"], key="f_est_pos")
            f_venc = st.date_input("Fecha Vencimiento", datetime.today(), key="f_venc_pos").strftime('%Y-%m-%d')

        st.markdown("<br>", unsafe_allow_html=True)
        btn_pre_guardar = st.button("🚀 Continuar y Procesar Transacción", use_container_width=True, type="primary")

    # --- VALIDACIÓN INICIAL DE CAMPOS ---
    if btn_pre_guardar:
        if f_monto <= 0:
            st.error("❌ El monto debe ser mayor a $0.00 MXN.")
        elif not f_concepto:
            st.error("❌ Por favor escribe un Concepto o Descripción.")
        else:
            # Guardamos temporalmente en sesión para abrir el modal
            st.session_state["transaccion_pendiente"] = {
                "fecha": f_fecha,
                "tipo": f_tipo_dinamico,
                "categoria": f_cat,
                "concepto": f_concepto,
                "monto": float(f_monto),
                "metodo_pago": f_pago,
                "asociado": f_asociado,
                "etiqueta_asociado": etiqueta_asociado,
                "lote_asociado": f_lote,
                "estado_deuda": f_estado,
                "fecha_vencimiento": f_venc
            }

    # --- VENTANA EMERGENTE (MODAL DE CONFIRMACIÓN DE EMPLEADO) ---
    if "transaccion_pendiente" in st.session_state:
        
        # Uso de st.dialog si está disponible en la versión de Streamlit, o fallback estructurado
        if hasattr(st, "dialog"):
            @st.dialog("👤 Confirmación de Responsable")
            def modal_confirmacion_empleado():
                tx = st.session_state["transaccion_pendiente"]
                st.write("### Resumen del Registro")
                st.info(f"**Tipo:** {tx['tipo']} | **Monto:** $ {tx['monto']:,.2f} MXN\n\n"
                        f"**Concepto:** {tx['concepto']}\n\n"
                        f"**{tx['etiqueta_asociado']}:** {tx['asociado']}")
                
                st.markdown("---")
                st.subheader("¿Qué empleado procesó esta transacción?")
                
                opciones_modal_emp = ["-- Seleccionar Empleado --"] + lista_empleados
                emp_seleccionado = st.selectbox("Empleado Responsable *", opciones_modal_emp, index=0)
                
                c_mod1, c_mod2 = st.columns(2)
                with c_mod1:
                    # Deshabilitado si no se ha seleccionado un empleado válido
                    es_invalido = (emp_seleccionado == "-- Seleccionar Empleado --")
                    if st.button("✅ Confirmar y Guardar", disabled=es_invalido, use_container_width=True, type="primary"):
                        auto_id = f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}"
                        nuevo_registro = {
                            "id": auto_id,
                            "fecha": tx["fecha"],
                            "tipo": tx["tipo"],
                            "categoria": tx["categoria"],
                            "concepto": tx["concepto"],
                            "monto": tx["monto"],
                            "metodo_pago": tx["metodo_pago"],
                            "asociado": tx["asociado"],
                            "empleado_responsable": emp_seleccionado,
                            "lote_asociado": tx["lote_asociado"],
                            "estado_deuda": tx["estado_deuda"],
                            "fecha_vencimiento": tx["fecha_vencimiento"]
                        }
                        if guardar_registro("finanzas", nuevo_registro, "id"):
                            st.success(f"¡Transacción guardada exitosamente! Registró: {emp_seleccionado}")
                            del st.session_state["transaccion_pendiente"]
                            time.sleep(1)
                            st.rerun()
                with c_mod2:
                    if st.button("❌ Cancelar", use_container_width=True):
                        del st.session_state["transaccion_pendiente"]
                        st.rerun()

            modal_confirmacion_empleado()

        else:
            # Fallback para versiones previas de Streamlit sin st.dialog
            with st.expander("👤 **SELECCIONAR EMPLEADO QUE REALIZA LA TRANSACCIÓN**", expanded=True):
                tx = st.session_state["transaccion_pendiente"]
                st.info(f"**{tx['tipo']}** de **$ {tx['monto']:,.2f} MXN** - Concepto: *{tx['concepto']}* ({tx['etiqueta_asociado']}: {tx['asociado']})")
                
                opciones_modal_emp = ["-- Seleccionar Empleado --"] + lista_empleados
                emp_seleccionado = st.selectbox("Selecciona Empleado Responsable *", opciones_modal_emp, index=0, key="exp_emp_sel")
                
                es_invalido = (emp_seleccionado == "-- Seleccionar Empleado --")
                col_exp1, col_exp2 = st.columns(2)
                
                with col_exp1:
                    if st.button("✅ Confirmar y Guardar Transacción", disabled=es_invalido, use_container_width=True, type="primary", key="btn_conf_exp"):
                        auto_id = f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}"
                        nuevo_registro = {
                            "id": auto_id,
                            "fecha": tx["fecha"],
                            "tipo": tx["tipo"],
                            "categoria": tx["categoria"],
                            "concepto": tx["concepto"],
                            "monto": tx["monto"],
                            "metodo_pago": tx["metodo_pago"],
                            "asociado": tx["asociado"],
                            "empleado_responsable": emp_seleccionado,
                            "lote_asociado": tx["lote_asociado"],
                            "estado_deuda": tx["estado_deuda"],
                            "fecha_vencimiento": tx["fecha_vencimiento"]
                        }
                        if guardar_registro("finanzas", nuevo_registro, "id"):
                            st.success(f"¡Transacción guardada exitosamente! Registró: {emp_seleccionado}")
                            del st.session_state["transaccion_pendiente"]
                            time.sleep(1)
                            st.rerun()
                with col_exp2:
                    if st.button("❌ Cancelar", use_container_width=True, key="btn_canc_exp"):
                        del st.session_state["transaccion_pendiente"]
                        st.rerun()

    # --- EDICIÓN MANUAL Y ELIMINACIÓN ---
    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        id_seleccionado = st.selectbox("Selecciona ID a alterar:", df_finanzas['id'].unique(), key="del_fin")
        fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
        
        try: fecha_orig = pd.to_datetime(fila_sel['fecha']).date()
        except: fecha_orig = datetime.today().date()
            
        try: f_venc_orig = pd.to_datetime(fila_sel.get('fecha_vencimiento', datetime.today())).date()
        except: f_venc_orig = datetime.today().date()
            
        with st.expander("📝 Abrir Editor Manual de la Transacción Seleccionada"):
            tipo_actual_bd = fila_sel.get('tipo', 'Egreso')
            idx_tipo_actual = 0 if tipo_actual_bd == "Ingreso" else 1
            edit_tipo = st.selectbox("Editar Tipo de Transacción", ["Ingreso", "Egreso"], index=idx_tipo_actual, key=f"ed_tipo_{id_seleccionado}")
            
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                edit_fecha = st.date_input("Fecha Transacción", value=fecha_orig, key=f"ed_fec_{id_seleccionado}").strftime('%Y-%m-%d')
                
                cats_posibles = cat_ingresos if edit_tipo == "Ingreso" else cat_costos_directos + cat_gastos_operativos
                cat_actual = fila_sel.get('categoria', '')
                idx_cat = cats_posibles.index(cat_actual) if cat_actual in cats_posibles else 0
                edit_cat = st.selectbox("Categoría", cats_posibles, index=idx_cat, key=f"ed_cat_{id_seleccionado}")
                
                edit_concepto = st.text_input("Concepto / Descripción", value=str(fila_sel.get('concepto', '')), key=f"ed_con_{id_seleccionado}").strip()
            
            with ec2:
                edit_monto = st.number_input("Monto ($ MXN)", value=float(fila_sel.get('monto', 0.0)), min_value=0.0, step=50.0, key=f"ed_mon_{id_seleccionado}")
                
                metodos_pago = ["Efectivo", "Transferencia", "Cheque", "Crédito"]
                met_actual = fila_sel.get('metodo_pago', 'Efectivo')
                idx_met = metodos_pago.index(met_actual) if met_actual in metodos_pago else 0
                edit_pago = st.selectbox("Método de Pago", metodos_pago, index=idx_met, key=f"ed_pag_{id_seleccionado}")
                
                edit_asociado = st.text_input("Cliente/Proveedor/Beneficiario", value=str(fila_sel.get('asociado', 'N/A')), key=f"ed_aso_{id_seleccionado}")

            with ec3:
                opciones_lotes_ed = ["Ninguno"]
                if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                    opciones_lotes_ed += list(df_lotes['nombre_lote'].dropna().unique())
                lote_actual = fila_sel.get('lote_asociado', 'Ninguno')
                idx_lote = opciones_lotes_ed.index(lote_actual) if lote_actual in opciones_lotes_ed else 0
                edit_lote = st.selectbox("Lote Asociado", opciones_lotes_ed, index=idx_lote, key=f"ed_lot_{id_seleccionado}")
                
                estados = ["Pagado", "Pendiente"]
                est_actual = fila_sel.get('estado_deuda', 'Pagado')
                idx_est = estados.index(est_actual) if est_actual in estados else 0
                edit_estado = st.selectbox("Estado del Pago", estados, index=idx_est, key=f"ed_est_{id_seleccionado}")
                edit_venc = st.date_input("Fecha Vencimiento", value=f_venc_orig, key=f"ed_venc_{id_seleccionado}").strftime('%Y-%m-%d')
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("💾 Actualizar Registro", use_container_width=True, key=f"btn_act_{id_seleccionado}"):
                    if edit_monto <= 0:
                        st.error("❌ El monto debe ser mayor a $0.00 MXN.")
                    elif not edit_concepto:
                        st.error("❌ El concepto no puede estar vacío.")
                    else:
                        registro_editado = {
                            "id": id_seleccionado,
                            "fecha": edit_fecha,
                            "tipo": edit_tipo,
                            "categoria": edit_cat,
                            "concepto": edit_concepto,
                            "monto": float(edit_monto),
                            "metodo_pago": edit_pago,
                            "asociado": edit_asociado,
                            "empleado_responsable": fila_sel.get('empleado_responsable', 'N/A'),
                            "lote_asociado": edit_lote,
                            "estado_deuda": edit_estado,
                            "fecha_vencimiento": edit_venc
                        }
                        if guardar_registro("finanzas", registro_editado, "id"):
                            st.success(f"¡Registro {id_seleccionado} actualizado exitosamente!")
                            time.sleep(1)
                            st.rerun()
            
            with btn_col2:
                if st.button("🗑️ Eliminar Transacción", use_container_width=True, type="primary", key=f"btn_elim_{id_seleccionado}"):
                    if eliminar_registro("finanzas", id_seleccionado, "id"):
                        st.warning(f"Se ha eliminado el registro ID: {id_seleccionado}")
                        time.sleep(1)
                        st.rerun()
# MÓDULO 2: EMPLEADOS
elif modulo_activo == "🤠 Personal / Empleados":
    st.header("🤠 Administración de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        e_nombre = st.text_input("Nombre del Empleado").strip().upper()
        e_tel = st.text_input("Teléfono (10 dígitos)").strip()
        e_puesto = st.text_input("Puesto").strip().upper()
        submit_empleado = st.form_submit_button("💾 Guardar Empleado", use_container_width=True)
        
        if submit_empleado:
            if not e_nombre:
                st.error("❌ El nombre del empleado es obligatorio.")
            elif e_tel and (not e_tel.isdigit() or len(e_tel) != 10):
                st.error("❌ El teléfono debe constar exactamente de 10 dígitos numéricos.")
            else:
                if guardar_registro("empleados", {"nombre": e_nombre, "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": datetime.today().strftime('%Y-%m-%d')}, "nombre"):
                    st.success("Empleado guardado correctamente.")
                    time.sleep(0.4)
                    st.rerun()
                
    col_bus_emp, col_rep_emp = st.columns([3, 1])
    with col_bus_emp:
        buscar_emp = st.text_input("🔍 Buscar Empleado:", key="bus_emp").strip()
        
    df_emp_vista = df_empleados.copy()
    if not df_emp_vista.empty:
        if buscar_emp:
            df_emp_vista = df_emp_vista[df_emp_vista.astype(str).apply(lambda x: x.str.contains(buscar_emp, case=False)).any(axis=1)]
            
        with col_rep_emp:
            st.write("")
            html_emp = generar_html_docs("Listado de Personal", ["Nombre", "Teléfono", "Puesto/Función", "Fecha Ingreso"], df_emp_vista, ["nombre", "telefono", "puesto_funcion", "fecha_ingreso"])
            st.download_button(
                label="📄 Generar Reporte Personal (Docs)",
                data=html_emp,
                file_name=f"Reporte_Empleados_{datetime.now().strftime('%Y%m%d')}.doc",
                mime="application/msword",
                use_container_width=True
            )
            
    st.dataframe(df_emp_vista, use_container_width=True, hide_index=True)
    
    if not df_empleados.empty:
        emp_sel = st.selectbox("Selecciona Empleado para Eliminar:", df_empleados['nombre'].unique())
        if st.button("🗑️ Eliminar Empleado", type="primary"):
            if eliminar_registro("empleados", "nombre", emp_sel):
                time.sleep(0.4)
                st.rerun()

# MÓDULO 3: CLIENTES
elif modulo_activo == "🤝 Clientes":
    st.header("🤝 Registro y Catálogo de Clientes")
    with st.form("form_clientes", clear_on_submit=True):
        c_nombre = st.text_input("Razón Social / Nombre").strip().upper()
        c_tel = st.text_input("Teléfono (10 dígitos)").strip()
        submit_cliente = st.form_submit_button("💾 Guardar Cliente", use_container_width=True)
        
        if submit_cliente:
            if not c_nombre:
                st.error("❌ El nombre o razón social es obligatorio.")
            elif c_tel and (not c_tel.isdigit() or len(c_tel) != 10):
                st.error("❌ El teléfono debe constar exactamente de 10 dígitos numéricos.")
            else:
                if guardar_registro("clientes", {"nombre_razon": c_nombre, "telefono": c_tel}, "nombre_razon"):
                    st.success("Cliente guardado correctamente.")
                    time.sleep(0.4)
                    st.rerun()
                
    col_bus_cli, col_rep_cli = st.columns([3, 1])
    with col_bus_cli:
        buscar_cli = st.text_input("🔍 Buscar Cliente:", key="bus_cli").strip()
        
    df_cli_vista = df_clientes.copy()
    if not df_cli_vista.empty:
        if buscar_cli:
            df_cli_vista = df_cli_vista[df_cli_vista.astype(str).apply(lambda x: x.str.contains(buscar_cli, case=False)).any(axis=1)]
            
        with col_rep_cli:
            st.write("")
            html_cli = generar_html_docs("Catálogo de Clientes", ["Nombre/Razón Social", "Teléfono"], df_cli_vista, ["nombre_razon", "telefono"])
            st.download_button(
                label="📄 Generar Reporte Clientes (Docs)",
                data=html_cli,
                file_name=f"Reporte_Clientes_{datetime.now().strftime('%Y%m%d')}.doc",
                mime="application/msword",
                use_container_width=True
            )
            
    st.dataframe(df_cli_vista, use_container_width=True, hide_index=True)
    
    if not df_clientes.empty:
        st.markdown("#### 🛠️ Editar o Eliminar Cliente")
        cli_sel = st.selectbox("Selecciona un Cliente:", df_clientes['nombre_razon'].unique(), key="sel_cli_edit")
        fila_cli = df_clientes[df_clientes['nombre_razon'] == cli_sel].iloc[0]
        
        with st.expander(f"📝 Editar Datos de {cli_sel}"):
            edit_cli_tel = st.text_input("Modificar Teléfono:", str(fila_cli.get('telefono', '')), key=f"tel_cli_{cli_sel}").strip()
            
            c_act, c_elim = st.columns(2)
            with c_act:
                if st.button("🔄 Actualizar Teléfono", key=f"btn_up_cli_{cli_sel}", use_container_width=True):
                    if edit_cli_tel and (not edit_cli_tel.isdigit() or len(edit_cli_tel) != 10):
                        st.error("El teléfono debe tener 10 números.")
                    else:
                        if guardar_registro("clientes", {"nombre_razon": cli_sel, "telefono": edit_cli_tel}, "nombre_razon"):
                            st.success("¡Cliente actualizado con éxito!")
                            time.sleep(0.4)
                            st.rerun()
            with c_elim:
                if st.button("🗑️ Eliminar Cliente", key=f"btn_del_cli_{cli_sel}", use_container_width=True, type="primary"):
                    if eliminar_registro("clientes", "nombre_razon", cli_sel):
                        time.sleep(0.4)
                        st.rerun()

# MÓDULO 4: PROVEEDORES
elif modulo_activo == "🚜 Proveedores":
    st.header("🚜 Catálogo de Proveedores")
    with st.form("form_proveedores", clear_on_submit=True):
        p_nombre = st.text_input("Nombre del Proveedor / Razón Social").strip().upper()
        p_insumo = st.text_input("Insumo Principal (Ej: Alimento, Medicinas, Diésel)").strip().upper()
        p_contacto = st.text_input("Información de Contacto (Teléfono / Correo)").strip()
        submit_prov = st.form_submit_button("💾 Guardar Proveedor", use_container_width=True)
        
        if submit_prov:
            if not p_nombre.strip():
                st.error("❌ El nombre del proveedor es obligatorio.")
            else:
                datos_proveedor = {"nombre_proveedor": p_nombre, "insumo_principal": p_insumo, "contacto": p_contacto}
                if guardar_registro("proveedores", datos_proveedor, "nombre_proveedor"):
                    st.success("Proveedor guardado correctamente.")
                    time.sleep(0.4)
                    st.rerun()
                    
    col_bus_prov, col_rep_prov = st.columns([3, 1])
    with col_bus_prov:
        buscar_prov = st.text_input("🔍 Buscar Proveedor:", key="bus_prov").strip()
        
    df_prov_vista = df_proveedores.copy()
    if not df_prov_vista.empty:
        columnas_prov = ["nombre_proveedor", "insumo_principal"]
        if "contacto" in df_prov_vista.columns:
            columnas_prov.append("contacto")
        df_prov_vista = df_prov_vista.reindex(columns=columnas_prov)
        
        if buscar_prov:
            df_prov_vista = df_prov_vista[df_prov_vista.astype(str).apply(lambda x: x.str.contains(buscar_prov, case=False)).any(axis=1)]
            
        with col_rep_prov:
            st.write("")
            html_prov = generar_html_docs("Registro de Proveedores", ["Nombre Proveedor", "Insumo Principal", "Contacto"], df_prov_vista, ["nombre_proveedor", "insumo_principal", "contacto"])
            st.download_button(
                label="📄 Generar Reporte Proveedores (Docs)",
                data=html_prov,
                file_name=f"Reporte_Proveedores_{datetime.now().strftime('%Y%m%d')}.doc",
                mime="application/msword",
                use_container_width=True
            )
            
    st.dataframe(df_prov_vista, use_container_width=True, hide_index=True)
        
    if not df_proveedores.empty:
        prov_sel = st.selectbox("Selecciona Proveedor para Eliminar:", df_proveedores['nombre_proveedor'].unique())
        if st.button("🗑️ Eliminar Proveedor", type="primary"):
            if eliminar_registro("proveedores", "nombre_proveedor", prov_sel):
                time.sleep(0.4)
                st.rerun()

# MÓDULO 5: CONTROL DE LOTES
elif modulo_activo == "🐂 Control de Lotes":
    st.header("🐂 Control de Lotes de Ganado")
    with st.form("form_lotes", clear_on_submit=True):
        l_nombre = st.text_input("Código del Lote (Ej: LOTE_SARDO_01)").strip().upper()
        col_lote_1, col_lote_2 = st.columns(2)
        with col_lote_1:
            l_cabezas = st.number_input("Número de cabezas de ganado:", min_value=0, step=1, value=10)
        with col_lote_2:
            l_raza = st.text_input("Raza / Genética preponderante (Ej: SARDO NEGRO, SUIZBU):").strip().upper()
            
        l_desc = st.text_area("Notas Adicionales de Alimentación o Potrero").strip()
        submit_lote = st.form_submit_button("💾 Guardar Lote", use_container_width=True)
        
        if submit_lote:
            if not l_nombre.strip():
                st.error("❌ El código del lote es obligatorio para el control administrativo.")
            else:
                registro_lote = {
                    "nombre_lote": l_nombre, 
                    "cabezas": int(l_cabezas),
                    "raza": l_raza,
                    "descripcion_notas": l_desc, 
                    "fecha_creacion": datetime.today().strftime('%Y-%m-%d')
                }
                if guardar_registro("lotes", registro_lote, "nombre_lote"):
                    st.success(f"¡Lote {l_nombre} guardado con éxito con datos estructurados!")
                    time.sleep(0.4)
                    st.rerun()
                
    col_bus_lot, col_rep_lot = st.columns([3, 1])
    with col_bus_lot:
        buscar_lote = st.text_input("🔍 Buscar Lote:", key="bus_lote").strip()
        
    df_lotes_vista = df_lotes.copy()
    if not df_lotes_vista.empty:
        if buscar_lote:
            df_lotes_vista = df_lotes_vista[df_lotes_vista.astype(str).apply(lambda x: x.str.contains(buscar_lote, case=False)).any(axis=1)]
            
        with col_rep_lot:
            st.write("")
            html_lot = generar_html_docs("Inventario de Lotes de Ganado", ["Código Lote", "Cabezas", "Raza/Genética", "Notas/Potrero", "Fecha Creación"], df_lotes_vista, ["nombre_lote", "cabezas", "raza", "descripcion_notas", "fecha_creacion"])
            st.download_button(
                label="📄 Generar Reporte Lotes (Docs)",
                data=html_lot,
                file_name=f"Reporte_Lotes_{datetime.now().strftime('%Y%m%d')}.doc",
                mime="application/msword",
                use_container_width=True
            )
            
    st.dataframe(df_lotes_vista, use_container_width=True, hide_index=True)
    
    # Edición Manual de Lotes
    if not df_lotes.empty:
        st.markdown("#### 🛠️ Editar o Eliminar Lote de Ganado")
        lote_sel = st.selectbox("Selecciona un Lote para Modificar:", df_lotes['nombre_lote'].unique(), key="sel_lot_edit")
        fila_lot = df_lotes[df_lotes['nombre_lote'] == lote_sel].iloc[0]
        
        with st.expander(f"📝 Modificar Parámetros de {lote_sel}"):
            le_c1, le_c2 = st.columns(2)
            with le_c1:
                edit_lot_cabezas = st.number_input("Corregir Cabezas:", min_value=0, step=1, value=int(fila_lot.get('cabezas', 0)) if pd.notnull(fila_lot.get('cabezas')) else 0, key=f"cab_{lote_sel}")
            with le_c2:
                edit_lot_raza = st.text_input("Corregir Raza/Genética:", str(fila_lot.get('raza', '')), key=f"raz_{lote_sel}").strip().upper()
            
            edit_lot_desc = st.text_area("Modificar Notas / Potrero:", str(fila_lot.get('descripcion_notas', fila_lot.get('descripcion_notes', ''))), key=f"desc_{lote_sel}").strip()
            
            l_act, l_elim = st.columns(2)
            with l_act:
                if st.button("🔄 Guardar Cambios en Lote", key=f"btn_up_lot_{lote_sel}", use_container_width=True):
                    registro_lote_act = {
                        "nombre_lote": lote_sel,
                        "cabezas": int(edit_lot_cabezas),
                        "raza": edit_lot_raza,
                        "descripcion_notas": edit_lot_desc,
                        "fecha_creacion": str(fila_lot.get('fecha_creacion', datetime.today().strftime('%Y-%m-%d')))
                    }
                    if guardar_registro("lotes", registro_lote_act, "nombre_lote"):
                        st.success("¡Lote actualizado en Supabase!")
                        time.sleep(0.4)
                        st.rerun()
            with l_elim:
                if st.button("🗑️ Eliminar Lote Completo", key=f"btn_del_lot_{lote_sel}", use_container_width=True, type="primary"):
                    if eliminar_registro("lotes", "nombre_lote", lote_sel):
                        time.sleep(0.4)
                        st.rerun()
