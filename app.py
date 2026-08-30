import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import base64
import time
import json
import os
import pytz
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA (¡DEBE SER EL PRIMER COMANDO DE STREAMLIT!)
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

# Estilos CSS Globales
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

# -------------------------------------------------------------
# 2. CONTROL DE SESIÓN Y CARGA DE USUARIOS
# -------------------------------------------------------------
TIEMPO_EXPIRED = 600  # 10 minutos

if "usuarios" in st.secrets:
    USUARIOS = {str(k).strip().lower(): str(v).strip() for k, v in st.secrets["usuarios"].items()}
else:
    USUARIOS = {"gerardo": "ADMINpg120214"}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None

def cerrar_sesion():
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.rerun()

# -------------------------------------------------------------
# 3. PANTALLA DE LOGIN
# -------------------------------------------------------------
if not st.session_state.autenticado:
    st.title("🔒 Inicia sesión para continuar")
    
    usuario_ingresado = st.text_input("Usuario")
    clave_ingresada = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar", use_container_width=True):
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
# 4. BARRA LATERAL - SESIÓN
# -------------------------------------------------------------
with st.sidebar:
    st.write(f"👤 Hola, **{st.session_state.usuario_actual.capitalize()}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        cerrar_sesion()

# ==========================================
# 5. VALIDACIÓN Y CONEXIÓN SUPABASE
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

st.title("Rancho AE: Sistema de Administración")
st.markdown("---")

# ==========================================
# FUNCIONES AUXILIARES Y DE REPORTES HTML
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
            <thead>
                <tr>
    """
    for header in columnas_headers:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
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
        <p style='margin-top:40px; font-size:11px; color:#999; text-align: center; border-top: 1px dashed #ccc; padding-top: 10px;'>
            Documento administrativo confidencial generado por el Sistema de Control Interno Rancho AE.
        </p>
    </body>
    </html>
    """
    return html

def generar_reporte_finanzas_profesional(df_datos, periodo, lote, ing, egr, net, cob, pag):
    hoy_str = obtener_fecha_hora_mx()
    
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
        <div class="header-title">RANCHO AE</div>
        <div class="header-subtitle">Informe Ejecutivo de Control Financiero y Estado de Resultados</div>
        <div class="divider"></div>
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
        <div class="section-title">3. Registro Detallado de Transacciones ({len(df_datos)} movimientos)</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Fecha</th><th>Tipo</th><th>Categoría</th><th>Concepto / Descripción</th>
                    <th>Lote</th><th>Método</th><th>Estado</th><th class="text-right">Monto (MXN)</th>
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
            Este balance ejecutivo constituye un extracto oficial de la contabilidad interna de Rancho AE.
        </p>
    </body>
    </html>
    """
    return html

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

# ==========================================
# MÓDULO 1: DASHBOARD Y FINANZAS
# ==========================================
if modulo_activo == "📊 Dashboard & Finanzas":
    st.header("📊 Balance y Control General Financiero")

    cat_ingresos = ["Venta de ganado", "Varios (Ingresos)", "Préstamo / Crédito recibido"]
    cat_costos_directos = ["Compra de ganado", "Alimentos", "Medicamentos", "Servicios veterinarios", "Dosis de semen", "Varios (Costos directos)"]
    cat_gastos_operativos = ["Gastos de oficina", "Arriendo", "Nomina", "Combustible", "Mantenimiento", "Pago / Abono Préstamo", "Varios (Gastos operativos)"]

    lista_clientes = ["Público en general"]
    if not df_clientes.empty:
        col_c = 'nombre' if 'nombre' in df_clientes.columns else df_clientes.columns[0]
        lista_clientes += [c for c in df_clientes[col_c].dropna().unique() if c != "Público en general"]

    lista_proveedores = ["Egreso general", "Institución Financiera / Banco"]
    if not df_proveedores.empty:
        col_p = 'nombre' if 'nombre' in df_proveedores.columns else df_proveedores.columns[0]
        lista_proveedores += [p for p in df_proveedores[col_p].dropna().unique() if p not in lista_proveedores]

    lista_empleados = []
    if not df_empleados.empty:
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
        df_pendientes = df_finanzas[df_finanzas['estado_deuda'] == 'Pendiente'].copy()
        
        if not df_pendientes.empty:
            df_pendientes['saldo_pendiente'] = df_pendientes['monto'] - df_pendientes['abono_acumulado']
            df_cobrar_pend = df_pendientes[(df_pendientes['tipo'] == 'Ingreso') & (df_pendientes['categoria'] != 'Préstamo / Crédito recibido')]
            df_pagar_pend = df_pendientes[(df_pendientes['tipo'] == 'Egreso') | (df_pendientes['categoria'] == 'Préstamo / Crédito recibido')]

            df_vencidos_cobrar = df_cobrar_pend[df_cobrar_pend['fecha_vencimiento'] < hoy_dt] if 'fecha_vencimiento' in df_cobrar_pend.columns else pd.DataFrame()
            df_vencidos_pagar = df_pagar_pend[df_pagar_pend['fecha_vencimiento'] < hoy_dt] if 'fecha_vencimiento' in df_pagar_pend.columns else pd.DataFrame()

            if not df_vencidos_cobrar.empty or not df_vencidos_pagar.empty:
                with st.expander("🔔 **Alertas de Cuentas Pendientes y Vencimientos**", expanded=True):
                    col_al1, col_al2 = st.columns(2)
                    with col_al1:
                        st.markdown("#### 🟢 Cuentas por Cobrar (Te deben dinero)")
                        if not df_vencidos_cobrar.empty:
                            tot_vencido_cob = df_vencidos_cobrar['saldo_pendiente'].sum()
                            st.warning(f"⚠️ **{len(df_vencidos_cobrar)} cobros vencidos** (Saldo por cobrar: **$ {tot_vencido_cob:,.2f} MXN**).")
                            st.dataframe(df_vencidos_cobrar[['id', 'fecha_vencimiento', 'concepto', 'monto', 'abono_acumulado', 'saldo_pendiente']], use_container_width=True)
                        else:
                            st.success("No tienes cobros vencidos pendientes.")
                            
                    with col_al2:
                        st.markdown("#### 🔴 Cuentas por Pagar (Tú debes dinero)")
                        if not df_vencidos_pagar.empty:
                            tot_vencido_pag = df_vencidos_pagar['saldo_pendiente'].sum()
                            st.error(f"⚠️ **{len(df_vencidos_pagar)} deudas/préstamos vencidos** (Saldo a pagar: **$ {tot_vencido_pag:,.2f} MXN**).")
                            st.dataframe(df_vencidos_pagar[['id', 'fecha_vencimiento', 'concepto', 'monto', 'abono_acumulado', 'saldo_pendiente']], use_container_width=True)
                        else:
                            st.success("No tienes deudas vencidas pendientes.")

        st.subheader("📆 Filtros de Consulta")
        col_filtro, col_lote_filtro, col_estado_filtro, col_fechas = st.columns([2, 2, 2, 3])
        
        fecha_inicio = hoy_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = hoy_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        with col_filtro:
            periodo = st.selectbox("Período:", ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"])

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
                if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[1], datetime.max.time())

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

        ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado') & (df_filtrado['categoria'] != 'Préstamo / Crédito recibido')]['monto'].sum()
        egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
        balance_neto = ingresos - egresos
        
        df_pend_ing = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente') & (df_filtrado['categoria'] != 'Préstamo / Crédito recibido')]
        por_cobrar = (df_pend_ing['monto'] - df_pend_ing['abono_acumulado']).sum() if not df_pend_ing.empty else 0.0

        df_pend_egr = df_filtrado[((df_filtrado['tipo'] == 'Egreso') | (df_filtrado['categoria'] == 'Préstamo / Crédito recibido')) & (df_filtrado['estado_deuda'] == 'Pendiente')]
        por_pagar = (df_pend_egr['monto'] - df_pend_egr['abono_acumulado']).sum() if not df_pend_egr.empty else 0.0

        tab_resumen, tab_abonos, tab_graficas, tab_rentabilidad = st.tabs([
            "📋 Resumen Numérico", "💵 Gestión de Abonos y Créditos", "📈 Análisis Gráfico", "📊 Estados Financieros"
        ])
        
        with tab_resumen:
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("🟢 Ingresos Reales", f"$ {ingresos:,.2f} MXN")
            m2.metric("🔴 Egresos Reales", f"$ {egresos:,.2f} MXN")
            m3.metric("💰 Balance Neto", f"$ {balance_neto:,.2f} MXN")
            m4.metric("📈 Por Cobrar (Restante)", f"$ {por_cobrar:,.2f} MXN")
            m5.metric("📉 Por Pagar (Restante)", f"$ {por_pagar:,.2f} MXN")
            
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
                df_bal_estilizado = df_bal_vista.style.apply(colorear_filas_finanzas, axis=1).format({'monto': '$ {:,.2f} MXN', 'abono_acumulado': '$ {:,.2f} MXN'})
                st.dataframe(df_bal_estilizado, use_container_width=True)
            else:
                st.info("No hay registros que coincidan con la búsqueda.")

        with tab_abonos:
            st.subheader("💵 Realizar Abonos a Cuentas Pendientes y Préstamos")
            st.markdown("Selecciona una cuenta con saldo pendiente para abonar a la deuda o liquidarla por completo.")

            df_cuentas_abono = df_finanzas[df_finanzas['estado_deuda'] == 'Pendiente'].copy()
            if not df_cuentas_abono.empty:
                df_cuentas_abono['saldo_restante'] = df_cuentas_abono['monto'] - df_cuentas_abono['abono_acumulado']
                df_cuentas_abono = df_cuentas_abono[df_cuentas_abono['saldo_restante'] > 0]

            if not df_cuentas_abono.empty:
                df_cuentas_abono['opcion_texto'] = df_cuentas_abono.apply(
                    lambda x: f"[{x['id']}] {x['tipo'].upper()} | {x['concepto']} | Total: ${x['monto']:,.2f} | Resta: ${x['saldo_restante']:,.2f} MXN", axis=1
                )
                
                asig_sel_texto = st.selectbox("Selecciona la transacción o préstamo a abonar:", df_cuentas_abono['opcion_texto'].tolist(), key="sel_abono_cuenta")
                id_abono_sel = asig_sel_texto.split("]")[0].replace("[", "").strip()
                fila_abono = df_cuentas_abono[df_cuentas_abono['id'] == id_abono_sel].iloc[0]

                saldo_actual_pendiente = float(fila_abono['saldo_restante'])

                col_ab1, col_ab2, col_ab3 = st.columns(3)
                with col_ab1:
                    st.info(f"**Monto Original:** $ {fila_abono['monto']:,.2f} MXN")
                    st.warning(f"**Abonado Previamente:** $ {fila_abono['abono_acumulado']:,.2f} MXN")
                    st.error(f"**Saldo Pendiente Actual:** $ {saldo_actual_pendiente:,.2f} MXN")

                with col_ab2:
                    monto_abono = st.number_input("Monto del Abono ($ MXN)", min_value=0.01, max_value=saldo_actual_pendiente, value=saldo_actual_pendiente, step=50.0, key="monto_abono_usr")
                    metodo_pago_abono = st.selectbox("Método de Pago del Abono", ["Efectivo", "Transferencia", "Cheque"], key="met_pago_abono")

                with col_ab3:
                    fecha_abono = st.date_input("Fecha del Abono", datetime.today(), key="fec_abono_usr").strftime('%Y-%m-%d')
                    concepto_abono = st.text_input("Nota / Concepto del Abono", value=f"Abono a {fila_abono['concepto']}", key="con_abono_usr")

                if st.button("💳 Registrar Abono", use_container_width=True, type="primary"):
                    nuevo_abono_acumulado = float(fila_abono['abono_acumulado']) + float(monto_abono)
                    nuevo_estado = "Pagado" if nuevo_abono_acumulado >= float(fila_abono['monto']) else "Pendiente"
                    
                    registro_padre_actualizado = {
                        "id": fila_abono['id'],
                        "fecha": fila_abono['fecha'].strftime('%Y-%m-%d') if hasattr(fila_abono['fecha'], 'strftime') else str(fila_abono['fecha']),
                        "tipo": fila_abono['tipo'],
                        "categoria": fila_abono['categoria'],
                        "concepto": fila_abono['concepto'],
                        "monto": float(fila_abono['monto']),
                        "abono_acumulado": nuevo_abono_acumulado,
                        "metodo_pago": fila_abono.get('metodo_pago', 'Efectivo'),
                        "asociado": fila_abono.get('asociado', ''),
                        "empleado_responsable": fila_abono.get('empleado_responsable', ''),
                        "lote_asociado": fila_abono.get('lote_asociado', 'Ninguno'),
                        "estado_deuda": nuevo_estado,
                        "fecha_vencimiento": fila_abono['fecha_vencimiento'].strftime('%Y-%m-%d') if hasattr(fila_abono['fecha_vencimiento'], 'strftime') else str(fila_abono.get('fecha_vencimiento', ''))
                    }

                    tipo_movimiento_abono = "Egreso" if fila_abono['tipo'] == "Egreso" else "Ingreso"
                    categoria_abono = "Pago / Abono Préstamo" if "Préstamo" in str(fila_abono['categoria']) else fila_abono['categoria']
                    
                    registro_hijo_abono = {
                        "id": f"AB-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}",
                        "fecha": fecha_abono,
                        "tipo": tipo_movimiento_abono,
                        "categoria": categoria_abono,
                        "concepto": f"[ABONO PARCIAL] {concepto_abono} (Ref: {fila_abono['id']})",
                        "monto": float(monto_abono),
                        "abono_acumulado": float(monto_abono),
                        "metodo_pago": metodo_pago_abono,
                        "asociado": fila_abono.get('asociado', ''),
                        "empleado_responsable": fila_abono.get('empleado_responsable', ''),
                        "lote_asociado": fila_abono.get('lote_asociado', 'Ninguno'),
                        "estado_deuda": "Pagado",
                        "id_origen_abono": fila_abono['id']
                    }

                    if guardar_registro("finanzas", registro_padre_actualizado, "id") and guardar_registro("finanzas", registro_hijo_abono, "id"):
                        st.success(f"¡Abono de $ {monto_abono:,.2f} MXN registrado correctamente!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("🎉 No hay cuentas ni préstamos con saldo pendiente registrado actualmente.")

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
            st.subheader("📊 Estado de Resultados (P&L) y Liquidez Global")
            st.markdown("Cálculos expresados en **Pesos Mexicanos (MXN)** basados en el desempeño operativo y posición patrimonial.")
            
            # MÓDULO 1: SALDO INTEGRAL Y LIQUIDEZ GLOBAL
            efectivo_disponible = balance_neto
            saldo_integral = efectivo_disponible + por_cobrar - por_pagar

            st.write("### 💰 Saldo Integral y Liquidez Global")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("💵 Disponible (Caja/Bancos)", f"$ {efectivo_disponible:,.2f} MXN")
            m2.metric("📈 Por Cobrar (CXC)", f"$ {por_cobrar:,.2f} MXN")
            m3.metric("📉 Por Pagar (CXP)", f"- $ {por_pagar:,.2f} MXN")
            m4.metric("🏛️ Saldo Integral Neto", f"$ {saldo_integral:,.2f} MXN", delta=f"$ {por_cobrar - por_pagar:,.2f} MXN")
            m5.metric("🟢/🔴 Balance Operativo", f"$ {balance_neto:,.2f} MXN")

            st.write("---")

            # MÓDULO 2: PROYECCIÓN DE CASH FLOW (LIQUIDEZ FUTURA)
            st.write("### 📉 Proyección de Cash Flow (Liquidez Futura)")
            df_cf = df_finanzas[df_finanzas['estado_deuda'] == 'Pendiente'].copy()
            
            if not df_cf.empty and 'fecha_vencimiento' in df_cf.columns:
                df_cf['saldo_pendiente'] = df_cf['monto'] - df_cf['abono_acumulado']
                df_cf['flujo_neto'] = df_cf.apply(
                    lambda r: r['saldo_pendiente'] if (r['tipo'] == 'Ingreso' and r['categoria'] != 'Préstamo / Crédito recibido') 
                    else -r['saldo_pendiente'], axis=1
                )
                
                df_cf['Fecha_Proyeccion'] = pd.to_datetime(df_cf['fecha_vencimiento']).dt.date
                cf_diario = df_cf.groupby('Fecha_Proyeccion')['flujo_neto'].sum().reset_index().sort_values('Fecha_Proyeccion')
                cf_diario['saldo_proyectado'] = balance_neto + cf_diario['flujo_neto'].cumsum()
                
                import plotly.graph_objects as go
                fig_cf = go.Figure()
                fig_cf.add_trace(go.Scatter(
                    x=cf_diario['Fecha_Proyeccion'],
                    y=cf_diario['saldo_proyectado'],
                    mode='lines+markers',
                    name='Saldo Proyectado',
                    line=dict(color='#2E7D32', width=3)
                ))
                fig_cf.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Punto Crítico Liquidez (0 MXN)")
                fig_cf.update_layout(title="Evolución de Liquidez Estimada por Vencimientos", xaxis_title="Fecha Vencimiento", yaxis_title="Monto ($ MXN)")
                
                st.plotly_chart(fig_cf, use_container_width=True)
            else:
                st.info("No hay cuentas pendientes registradas con fecha de vencimiento para calcular la proyección.")

            st.write("---")

            # MÓDULO 3: ESTADO DE RESULTADOS (P&L TRADICIONAL CORREGIDO)
            df_pagados = df_filtrado[df_filtrado['estado_deuda'] == 'Pagado'].copy()
            
            if not df_pagados.empty:
                # Clasificación estricta por categoría
                tot_ingresos = df_pagados[(df_pagados['tipo'] == 'Ingreso') & (df_pagados['categoria'] != 'Préstamo / Crédito recibido')]['monto'].sum()
                tot_costos_directos = df_pagados[df_pagados['categoria'].isin(cat_costos_directos)]['monto'].sum()
                tot_gastos_operativos = df_pagados[df_pagados['categoria'].isin(cat_gastos_operativos)]['monto'].sum()
                
                # Otros gastos no categorizados explícitamente en Costos Directos o Gastos Operativos
                tot_otros = df_pagados[
                    (df_pagados['tipo'] == 'Egreso') & 
                    (~df_pagados['categoria'].isin(cat_costos_directos)) & 
                    (~df_pagados['categoria'].isin(cat_gastos_operativos))
                ]['monto'].sum()
                
                # Fórmulas Financieras Correctas
                utilidad_bruta = tot_ingresos - tot_costos_directos
                margen_bruto = (utilidad_bruta / tot_ingresos * 100) if tot_ingresos > 0 else 0.0
                
                tot_egresos_totales = tot_costos_directos + tot_gastos_operativos + tot_otros
                utilidad_neta = tot_ingresos - tot_egresos_totales
                margen_neto = (utilidad_neta / tot_ingresos * 100) if tot_ingresos > 0 else 0.0
                
                flujo_caja = balance_neto
                
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
                            <td style="padding:10px; font-weight:bold;">(+) INGRESOS TOTALES POR VENTAS</td>
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
    
    st.subheader("💳 Captura y Registro Financiero / Préstamos")
    f_tipo_dinamico = st.radio("Tipo de Movimiento:", ["Ingreso", "Egreso"], horizontal=True)
    
    with st.container():
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            f_fecha = st.date_input("Fecha Transacción", datetime.today(), key="f_fec_pos").strftime('%Y-%m-%d')
            opciones_categorias = cat_ingresos if f_tipo_dinamico == "Ingreso" else cat_costos_directos + cat_gastos_operativos
            f_cat = st.selectbox("Categoría", opciones_categorias, key="f_cat_pos")
            f_concepto = st.text_input("Concepto / Descripción", key="f_con_pos").strip()

        with col_f2:
            f_monto = st.number_input("Monto Total ($ MXN)", min_value=0.0, step=50.0, key="f_mon_pos")
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"], key="f_pag_pos")
            
            if f_tipo_dinamico == "Ingreso":
                if f_cat == "Préstamo / Crédito recibido":
                    f_asociado = st.selectbox("Institución / Prestamista", lista_proveedores, index=0, key="f_pres_prov_pos")
                    etiqueta_asociado = "Institución / Prestamista"
                else:
                    f_asociado = st.selectbox("Cliente / Origen", lista_clientes, index=0, key="f_cli_pos")
                    etiqueta_asociado = "Cliente"
            else:
                if f_cat == "Nomina":
                    if lista_empleados:
                        f_asociado = st.selectbox("Empleado Beneficiario (Nómina)", lista_empleados, index=0, key="f_emp_nom_pos")
                    else:
                        f_asociado = st.text_input("Empleado Beneficiario", "Empleado General", key="f_emp_nom_txt")
                    etiqueta_asociado = "Empleado Beneficiario"
                else:
                    f_asociado = st.selectbox("Proveedor / Destino", lista_proveedores, index=0, key="f_prov_pos")
                    etiqueta_asociado = "Proveedor"

        with col_f3:
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes, key="f_lot_pos")
            idx_est_defecto = 1 if f_cat == "Préstamo / Crédito recibido" else 0
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"], index=idx_est_defecto, key="f_est_pos")
            f_venc = st.date_input("Fecha Vencimiento", datetime.today(), key="f_venc_pos").strftime('%Y-%m-%d')

        st.markdown("<br>", unsafe_allow_html=True)
        btn_pre_guardar = st.button("Confirmar", use_container_width=True, type="primary")

    if btn_pre_guardar:
        if f_monto <= 0:
            st.error("❌ El monto debe ser mayor a $0.00 MXN.")
        elif not f_concepto:
            st.error("❌ Por favor escribe un Concepto o Descripción.")
        else:
            st.session_state["transaccion_pendiente"] = {
                "id": f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}",
                "fecha": f_fecha,
                "tipo": f_tipo_dinamico,
                "categoria": f_cat,
                "concepto": f_concepto,
                "monto": float(f_monto),
                "abono_acumulado": 0.0,
                "metodo_pago": f_pago,
                "asociado": f_asociado,
                "etiqueta_asociado": etiqueta_asociado,
                "lote_asociado": f_lote,
                "estado_deuda": f_estado,
                "fecha_vencimiento": f_venc,
                "es_edicion": False
            }
            st.rerun()

    if "transaccion_pendiente" in st.session_state:
        tx = st.session_state["transaccion_pendiente"]
        
        if hasattr(st, "dialog"):
            @st.dialog("👤 Confirmación de Responsable")
            def modal_confirmacion_empleado():
                accion_txt = "Edición" if tx.get("es_edicion", False) else "Registro"
                st.write(f"### Resumen de {accion_txt}")
                st.info(f"**ID:** {tx['id']} | **Tipo:** {tx['tipo']} | **Monto:** $ {tx['monto']:,.2f} MXN\n\n"
                        f"**Concepto:** {tx['concepto']}\n\n"
                        f"**{tx['etiqueta_asociado']}:** {tx['asociado']}")
                
                st.markdown("---")
                st.subheader("¿Qué empleado realiza/autoriza esta acción?")
                
                idx_emp_defecto = 0
                if tx.get("empleado_responsable") in lista_empleados:
                    idx_emp_defecto = lista_empleados.index(tx["empleado_responsable"]) + 1
                    
                opciones_modal_emp = ["-- Seleccionar Empleado --"] + lista_empleados
                emp_seleccionado = st.selectbox("Empleado Responsable *", opciones_modal_emp, index=idx_emp_defecto, key="modal_emp_sel")
                
                c_mod1, c_mod2 = st.columns(2)
                with c_mod1:
                    es_invalido = (emp_seleccionado == "-- Seleccionar Empleado --")
                    if st.button("✅ Confirmar y Guardar", disabled=es_invalido, use_container_width=True, type="primary", key="modal_btn_guardar"):
                        registro_final = {
                            "id": tx["id"],
                            "fecha": tx["fecha"],
                            "tipo": tx["tipo"],
                            "categoria": tx["categoria"],
                            "concepto": tx["concepto"],
                            "monto": tx["monto"],
                            "abono_acumulado": tx.get("abono_acumulado", 0.0),
                            "metodo_pago": tx["metodo_pago"],
                            "asociado": tx["asociado"],
                            "empleado_responsable": emp_seleccionado,
                            "lote_asociado": tx["lote_asociado"],
                            "estado_deuda": tx["estado_deuda"],
                            "fecha_vencimiento": tx["fecha_vencimiento"]
                        }
                        if guardar_registro("finanzas", registro_final, "id"):
                            st.success(f"¡Transacción procesada exitosamente! Registró/Modificó: {emp_seleccionado}")
                            del st.session_state["transaccion_pendiente"]
                            time.sleep(1)
                            st.rerun()
                with c_mod2:
                    if st.button("❌ Cancelar", use_container_width=True, key="modal_btn_cancelar"):
                        del st.session_state["transaccion_pendiente"]
                        st.rerun()

            modal_confirmacion_empleado()

        else:
            with st.expander("👤 **SELECCIONAR EMPLEADO RESPONSABLE**", expanded=True):
                accion_txt = "Edición" if tx.get("es_edicion", False) else "Registro"
                st.info(f"**{accion_txt} ({tx['id']})**: **{tx['tipo']}** por **$ {tx['monto']:,.2f} MXN** - *{tx['concepto']}* ({tx['etiqueta_asociado']}: {tx['asociado']})")
                
                idx_emp_defecto = 0
                if tx.get("empleado_responsable") in lista_empleados:
                    idx_emp_defecto = lista_empleados.index(tx["empleado_responsable"]) + 1
                    
                opciones_modal_emp = ["-- Seleccionar Empleado --"] + lista_empleados
                emp_seleccionado = st.selectbox("Selecciona Empleado Responsable *", opciones_modal_emp, index=idx_emp_defecto, key="exp_emp_sel")
                
                es_invalido = (emp_seleccionado == "-- Seleccionar Empleado --")
                col_exp1, col_exp2 = st.columns(2)
                
                with col_exp1:
                    if st.button("✅ Confirmar y Guardar", disabled=es_invalido, use_container_width=True, type="primary", key="btn_conf_exp"):
                        registro_final = {
                            "id": tx["id"],
                            "fecha": tx["fecha"],
                            "tipo": tx["tipo"],
                            "categoria": tx["categoria"],
                            "concepto": tx["concepto"],
                            "monto": tx["monto"],
                            "abono_acumulado": tx.get("abono_acumulado", 0.0),
                            "metodo_pago": tx["metodo_pago"],
                            "asociado": tx["asociado"],
                            "empleado_responsable": emp_seleccionado,
                            "lote_asociado": tx["lote_asociado"],
                            "estado_deuda": tx["estado_deuda"],
                            "fecha_vencimiento": tx["fecha_vencimiento"]
                        }
                        if guardar_registro("finanzas", registro_final, "id"):
                            st.success(f"¡Transacción procesada exitosamente! Registró/Modificó: {emp_seleccionado}")
                            del st.session_state["transaccion_pendiente"]
                            time.sleep(1)
                            st.rerun()
                with col_exp2:
                    if st.button("❌ Cancelar", use_container_width=True, key="btn_canc_exp"):
                        del st.session_state["transaccion_pendiente"]
                        st.rerun()

    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        id_seleccionado = st.selectbox("Selecciona ID a alterar:", df_finanzas['id'].unique(), key="del_fin")
        fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
        
        try:
            val_fec = pd.to_datetime(fila_sel.get('fecha'))
            fecha_orig = val_fec.date() if pd.notnull(val_fec) else datetime.today().date()
        except Exception:
            fecha_orig = datetime.today().date()
            
        try:
            val_venc = pd.to_datetime(fila_sel.get('fecha_vencimiento'))
            f_venc_orig = val_venc.date() if pd.notnull(val_venc) else datetime.today().date()
        except Exception:
            f_venc_orig = datetime.today().date()
            
        with st.expander("📝 Abrir Editor Manual"):
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
                
                asociado_previo = str(fila_sel.get('asociado', ''))
                
                if edit_tipo == "Ingreso":
                    lista_opciones_aso = lista_clientes
                    idx_aso = lista_opciones_aso.index(asociado_previo) if asociado_previo in lista_opciones_aso else 0
                    edit_asociado = st.selectbox("Cliente / Venta al Público", lista_opciones_aso, index=idx_aso, key=f"ed_aso_{id_seleccionado}")
                    etiqueta_asociado_ed = "Cliente"
                else:
                    if edit_cat == "Nomina":
                        if lista_empleados:
                            idx_aso = lista_empleados.index(asociado_previo) if asociado_previo in lista_empleados else 0
                            edit_asociado = st.selectbox("Empleado Beneficiario (Nómina)", lista_empleados, index=idx_aso, key=f"ed_aso_{id_seleccionado}")
                        else:
                            edit_asociado = st.text_input("Empleado Beneficiario", value=asociado_previo or "Empleado General", key=f"ed_aso_txt_{id_seleccionado}")
                        etiqueta_asociado_ed = "Empleado Beneficiario"
                    else:
                        lista_opciones_aso = lista_proveedores
                        idx_aso = lista_opciones_aso.index(asociado_previo) if asociado_previo in lista_opciones_aso else 0
                        edit_asociado = st.selectbox("Proveedor / Egreso General", lista_opciones_aso, index=idx_aso, key=f"ed_aso_{id_seleccionado}")
                        etiqueta_asociado_ed = "Proveedor"

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
                if st.button("💾 Guardar Cambios", use_container_width=True, key=f"btn_act_{id_seleccionado}"):
                    if edit_monto <= 0:
                        st.error("❌ El monto debe ser mayor a $0.00 MXN.")
                    elif not edit_concepto:
                        st.error("❌ Por favor escribe un Concepto o Descripción.")
                    else:
                        st.session_state["transaccion_pendiente"] = {
                            "id": id_seleccionado,
                            "fecha": edit_fecha,
                            "tipo": edit_tipo,
                            "categoria": edit_cat,
                            "concepto": edit_concepto,
                            "monto": float(edit_monto),
                            "abono_acumulado": float(fila_sel.get('abono_acumulado', 0.0)),
                            "metodo_pago": edit_pago,
                            "asociado": edit_asociado,
                            "etiqueta_asociado": etiqueta_asociado_ed,
                            "empleado_responsable": fila_sel.get('empleado_responsable', ''),
                            "lote_asociado": edit_lote,
                            "estado_deuda": edit_estado,
                            "fecha_vencimiento": edit_venc,
                            "es_edicion": True
                        }
                        st.rerun()

            with btn_col2:
                if st.button("🗑️ Eliminar Transacción", use_container_width=True, type="primary", key=f"btn_del_{id_seleccionado}"):
                    st.session_state[f"confirmar_eliminar_{id_seleccionado}"] = True

            if st.session_state.get(f"confirmar_eliminar_{id_seleccionado}", False):
                st.warning(f"⚠️ ¿Estás seguro de que deseas eliminar permanentemente la transacción **{id_seleccionado}**?")
                col_del_si, col_del_no = st.columns(2)
                with col_del_si:
                    if st.button("🔴 Sí, Eliminar", use_container_width=True, key=f"confirm_si_{id_seleccionado}"):
                        try:
                            id_origen = str(fila_sel.get('id_origen_abono', ''))
                            if not id_origen and '[ABONO PARCIAL]' in str(fila_sel.get('concepto', '')):
                                try:
                                    id_origen = fila_sel.get('concepto', '').split('(Ref: ')[1].replace(')', '').strip()
                                except Exception:
                                    id_origen = ""

                            if id_origen and id_origen in df_finanzas['id'].values:
                                fila_padre = df_finanzas[df_finanzas['id'] == id_origen].iloc[0]
                                nuevo_acumulado = max(0.0, float(fila_padre.get('abono_acumulado', 0.0)) - float(fila_sel.get('monto', 0.0)))
                                nuevo_est_padre = "Pagado" if nuevo_acumulado >= float(fila_padre.get('monto', 0.0)) else "Pendiente"
                                
                                reg_padre_revertido = {
                                    "id": fila_padre['id'],
                                    "fecha": str(fila_padre['fecha'])[:10],
                                    "tipo": fila_padre['tipo'],
                                    "categoria": fila_padre['categoria'],
                                    "concepto": fila_padre['concepto'],
                                    "monto": float(fila_padre['monto']),
                                    "abono_acumulado": nuevo_acumulado,
                                    "metodo_pago": fila_padre.get('metodo_pago', 'Efectivo'),
                                    "asociado": fila_padre.get('asociado', ''),
                                    "empleado_responsable": fila_padre.get('empleado_responsable', ''),
                                    "lote_asociado": fila_padre.get('lote_asociado', 'Ninguno'),
                                    "estado_deuda": nuevo_est_padre,
                                    "fecha_vencimiento": str(fila_padre.get('fecha_vencimiento', ''))[:10]
                                }
                                guardar_registro("finanzas", reg_padre_revertido, "id")

                            eliminar_registro("finanzas", "id", str(id_seleccionado))
                            st.success(f"Transacción {id_seleccionado} eliminada exitosamente.")
                            st.session_state[f"confirmar_eliminar_{id_seleccionado}"] = False
                            time.sleep(1)
                            st.rerun()
                        except Exception as err:
                            st.error(f"Error al eliminar la transacción: {err}")
                            
                with col_del_no:
                    if st.button("❌ Cancelar", use_container_width=True, key=f"confirm_no_{id_seleccionado}"):
                        st.session_state[f"confirmar_eliminar_{id_seleccionado}"] = False
                        st.rerun()
# ==========================================
# MÓDULO 2: EMPLEADOS
# ==========================================
elif modulo_activo == "🤠 Personal / Empleados":
    st.header("🤠 Administración de Personal y Empleados")

    tab_registro, tab_listado, tab_transacciones = st.tabs([
        "➕ Registrar / Editar Empleado", 
        "📋 Listado de Personal", 
        "📊 Historial de Transacciones"
    ])

    with tab_registro:
        modo_form = st.radio("Acción:", ["Registrar Nuevo Empleado", "Editar Empleado Existente"], horizontal=True)
        
        e_nombre_val, e_puesto_val, e_sueldo_val = "", "", 0.0
        e_fecha_val = datetime.today()
        e_periodo_val, e_direccion_val, e_tel_val, e_email_val, e_estatus_val = "Quincenal", "", "", "", "Activo"
        emp_a_editar = None

        if modo_form == "Editar Empleado Existente":
            if not df_empleados.empty and 'nombre' in df_empleados.columns:
                lista_empleados = [e for e in df_empleados['nombre'].dropna().unique() if str(e).strip()]
                if lista_empleados:
                    emp_a_editar = st.selectbox("Selecciona Empleado a Editar:", lista_empleados)
                    row_emp = df_empleados[df_empleados['nombre'] == emp_a_editar].iloc[0]
                    
                    e_nombre_val = str(row_emp.get('nombre', ''))
                    e_puesto_val = str(row_emp.get('puesto_funcion', ''))
                    try: e_sueldo_val = float(row_emp.get('sueldo', 0.0))
                    except: e_sueldo_val = 0.0
                        
                    try: e_fecha_val = datetime.strptime(str(row_emp.get('fecha_ingreso', '')), '%Y-%m-%d')
                    except: e_fecha_val = datetime.today()
                        
                    e_periodo_val = str(row_emp.get('periodo_nomina', 'Quincenal'))
                    e_direccion_val = str(row_emp.get('direccion', ''))
                    e_tel_val = str(row_emp.get('telefono', ''))
                    e_email_val = str(row_emp.get('email', ''))
                    e_estatus_val = str(row_emp.get('estatus', 'Activo'))
                else:
                    st.info("No hay nombres válidos registrados.")
            else:
                st.info("No hay empleados registrados para editar.")

        with st.form("form_empleados", clear_on_submit=False):
            st.subheader("Datos del Empleado")
            col1, col2 = st.columns(2)
            periodos_opciones = ["Semanal", "Catorcenal", "Quincenal", "Mensual"]
            idx_periodo = periodos_opciones.index(e_periodo_val) if e_periodo_val in periodos_opciones else 2
            
            with col1:
                e_nombre = st.text_input("Nombre Completo *", value=e_nombre_val).strip().upper()
                e_puesto = st.text_input("Puesto / Función", value=e_puesto_val).strip().upper()
                e_sueldo = st.number_input("Sueldo ($)", min_value=0.0, value=e_sueldo_val, step=100.0)
                e_fecha_ingreso = st.date_input("Fecha de Contratación", value=e_fecha_val)
                e_periodo = st.selectbox("Periodo de Nómina", periodos_opciones, index=idx_periodo)

            with col2:
                e_tel = st.text_input("Teléfono", value=e_tel_val).strip()
                e_email = st.text_input("Correo Electrónico", value=e_email_val).strip().lower()
                e_direccion = st.text_area("Dirección", value=e_direccion_val, height=80).strip().upper()
                e_estatus = st.selectbox("Estatus del Empleado", ["Activo", "Inactivo"], index=0 if e_estatus_val == "Activo" else 1)

            submit_label = "💾 Actualizar Empleado" if modo_form == "Editar Empleado Existente" else "💾 Guardar Empleado"
            submit_empleado = st.form_submit_button(submit_label, use_container_width=True)

            if submit_empleado:
                if not e_nombre:
                    st.error("❌ El nombre del empleado es obligatorio.")
                else:
                    datos_empleado = {
                        "nombre": e_nombre,
                        "puesto_funcion": e_puesto,
                        "sueldo": e_sueldo,
                        "fecha_ingreso": e_fecha_ingreso.strftime('%Y-%m-%d'),
                        "periodo_nomina": e_periodo,
                        "direccion": e_direccion,
                        "telefono": e_tel,
                        "email": e_email,
                        "estatus": e_estatus
                    }
                    if guardar_registro("empleados", datos_empleado, "nombre"):
                        st.success(f"Empleado {'actualizado' if modo_form == 'Editar Empleado Existente' else 'guardado'} correctamente.")
                        time.sleep(0.4)
                        st.rerun()

    with tab_listado:
        col_bus_emp, col_rep_emp = st.columns([3, 1])
        with col_bus_emp:
            buscar_emp = st.text_input("🔍 Buscar Empleado:", key="bus_emp").strip()

        if not df_empleados.empty:
            df_emp_vista = df_empleados.copy()

            if buscar_emp:
                df_emp_vista = df_emp_vista[df_emp_vista.astype(str).apply(lambda x: x.str.contains(buscar_emp, case=False)).any(axis=1)]

            with col_rep_emp:
                st.write("")
                html_emp = generar_html_docs(
                    "Listado de Personal", 
                    ["Nombre", "Puesto", "Sueldo", "Fecha Ingreso", "Nómina", "Teléfono", "E-mail", "Estatus"], 
                    df_emp_vista, 
                    [c for c in ["nombre", "puesto_funcion", "sueldo", "fecha_ingreso", "periodo_nomina", "telefono", "email", "estatus"] if c in df_emp_vista.columns]
                )
                st.download_button(
                    label="📄 Generar Reporte (Docs)",
                    data=html_emp,
                    file_name=f"Reporte_Empleados_{datetime.now().strftime('%Y%m%d')}.doc",
                    mime="application/msword",
                    use_container_width=True
                )

            st.dataframe(
                df_emp_vista,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "periodo_nomina": st.column_config.TextColumn("Periodo Nómina"),
                    "estatus": st.column_config.TextColumn("Estatus"),
                    "sueldo": st.column_config.NumberColumn("Sueldo ($)", format="$%.2f")
                }
            )

            st.divider()
            col_del1, col_del2 = st.columns(2)
            lista_emp_elim = [e for e in df_empleados['nombre'].dropna().unique() if str(e).strip()] if 'nombre' in df_empleados.columns else []

            if lista_emp_elim:
                with col_del1:
                    st.subheader("🗑️ Eliminar / Inactivar Empleado")
                    emp_sel = st.selectbox("Selecciona Empleado:", lista_emp_elim, key="sel_del_emp")
                
                with col_del2:
                    st.write("###")
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("⚠️ Cambiar a Inactivo", use_container_width=True):
                            datos_inactivo = df_empleados[df_empleados['nombre'] == emp_sel].iloc[0].to_dict()
                            datos_inactivo['estatus'] = "Inactivo"
                            if guardar_registro("empleados", datos_inactivo, "nombre"):
                                st.warning(f"Empleado {emp_sel} marcado como Inactivo.")
                                time.sleep(0.4)
                                st.rerun()

                    with col_btn2:
                        if st.button("🗑️ Eliminar Definitivo", type="primary", use_container_width=True):
                            if eliminar_registro("empleados", "nombre", emp_sel):
                                st.success(f"Empleado {emp_sel} eliminado permanentemente.")
                                time.sleep(0.4)
                                st.rerun()
        else:
            st.info("No hay información de empleados registrada.")

    with tab_transacciones:
        st.subheader("📊 Transacciones Registradas por Empleado")
        if not df_finanzas.empty:
            df_tx_base = df_finanzas.copy()
            col_emp_tx = 'empleado_responsable' if 'empleado_responsable' in df_tx_base.columns else ('asociado' if 'asociado' in df_tx_base.columns else None)

            if col_emp_tx:
                df_tx_base[col_emp_tx] = df_tx_base[col_emp_tx].astype(str).str.strip().str.upper()

            col_f1, col_f2 = st.columns([2, 2])
            with col_f1:
                opciones_empleados = ["TODOS"]
                if not df_empleados.empty:
                    col_e_nombre = 'nombre' if 'nombre' in df_empleados.columns else df_empleados.columns[0]
                    opciones_empleados += list(df_empleados[col_e_nombre].dropna().astype(str).str.strip().str.upper().unique())
                
                if col_emp_tx:
                    unicos_tx = [e for e in df_tx_base[col_emp_tx].dropna().unique() if e not in opciones_empleados and e not in ["NONE", "NAN"]]
                    opciones_empleados += unicos_tx

                filtro_emp_tx = st.selectbox("Filtrar por Empleado Responsable:", opciones_empleados, key="sb_filtro_emp_tx")

            df_tx_display = df_tx_base.copy()
            if filtro_emp_tx != "TODOS" and col_emp_tx:
                df_tx_display = df_tx_display[df_tx_display[col_emp_tx] == filtro_emp_tx]

            if 'monto' in df_tx_display.columns:
                df_tx_display['monto'] = pd.to_numeric(df_tx_display['monto'], errors='coerce').fillna(0.0)

            if not df_tx_display.empty:
                st.dataframe(df_tx_display, use_container_width=True, hide_index=True)
            else:
                st.info(f"No hay transacciones registradas para el empleado **{filtro_emp_tx}**.")
        else:
            st.info("No se encontraron registros financieros cargados.")

# ==========================================
# MÓDULO 3: CLIENTES
# ==========================================
elif modulo_activo == "🤝 Clientes":
    st.header("🤝 Registro y Catálogo de Clientes")

    if not df_clientes.empty:
        col_m1, col_m2 = st.columns(2)
        with col_m1: st.metric("Total de Clientes", len(df_clientes))
        with col_m2: st.metric("Catálogo Actualizado", datetime.now().strftime("%d/%m/%Y"))
    st.markdown("---")

    with st.expander("➕ **Registrar Nuevo Cliente**", expanded=True):
        with st.form("form_clientes", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                c_nombre = st.text_input("Razón Social / Nombre *").strip().upper()
                c_tel = st.text_input("Teléfono (10 dígitos)").strip()
            with col_f2:
                c_email = st.text_input("Correo Electrónico (E-mail)").strip().lower()
                c_dir = st.text_input("Dirección / Ubicación").strip()

            submit_cliente = st.form_submit_button("💾 Guardar Cliente", use_container_width=True)

            if submit_cliente:
                if not c_nombre:
                    st.error("❌ El nombre o razón social es obligatorio.")
                elif c_tel and (not c_tel.isdigit() or len(c_tel) != 10):
                    st.error("❌ El teléfono debe constar exactamente de 10 dígitos numéricos.")
                elif c_email and ("@" not in c_email or "." not in c_email):
                    st.error("❌ Por favor, ingresa un correo electrónico válido.")
                else:
                    datos_nuevo = {"nombre_razon": c_nombre, "telefono": c_tel, "email": c_email, "direccion": c_dir}
                    if guardar_registro("clientes", datos_nuevo, "nombre_razon"):
                        st.success(f"¡Cliente '{c_nombre}' guardado correctamente!")
                        time.sleep(0.4)
                        st.rerun()

    st.markdown("### 📋 Catálogo de Clientes")
    col_bus_cli, col_rep_cli = st.columns([3, 1])
    
    with col_bus_cli:
        buscar_cli = st.text_input("🔍 Buscar por Nombre, Teléfono, Email o Dirección:", key="bus_cli").strip()

    df_cli_vista = df_clientes.copy()
    if not df_cli_vista.empty:
        if buscar_cli:
            df_cli_vista = df_cli_vista[df_cli_vista.astype(str).apply(lambda x: x.str.contains(buscar_cli, case=False)).any(axis=1)]

        with col_rep_cli:
            st.write("")
            html_cli = generar_html_docs("Catálogo de Clientes", ["Nombre/Razón Social", "Teléfono", "E-mail", "Dirección"], df_cli_vista, ["nombre_razon", "telefono", "email", "direccion"])
            st.download_button(label="📄 Reporte (Docs)", data=html_cli, file_name=f"Reporte_Clientes_{datetime.now().strftime('%Y%m%d')}.doc", mime="application/msword", use_container_width=True)

        st.dataframe(df_cli_vista, use_container_width=True, hide_index=True)

    if not df_clientes.empty:
        st.markdown("---")
        st.markdown("#### 🛠️ Gestionar Cliente (Editar o Eliminar)")
        cli_sel = st.selectbox("Selecciona un Cliente para modificar:", df_clientes['nombre_razon'].unique(), key="sel_cli_edit")
        
        if cli_sel:
            fila_cli = df_clientes[df_clientes['nombre_razon'] == cli_sel].iloc[0]

            col_acc1, col_acc2 = st.columns(2)
            with col_acc1:
                tel_val = str(fila_cli.get('telefono', '')).strip()
                if tel_val and len(tel_val) == 10:
                    st.link_button(f"💬 Abrir WhatsApp ({tel_val})", f"https://wa.me/52{tel_val}", use_container_width=True)
            with col_acc2:
                email_val = str(fila_cli.get('email', '')).strip()
                if email_val:
                    st.link_button(f"✉️ Enviar Correo", f"mailto:{email_val}", use_container_width=True)

            with st.expander(f"📝 Editar datos de: {cli_sel}", expanded=False):
                with st.form(key=f"form_edit_{cli_sel}"):
                    e_col1, e_col2 = st.columns(2)
                    with e_col1:
                        edit_nombre = st.text_input("Nombre / Razón Social:", str(fila_cli.get('nombre_razon', ''))).strip().upper()
                        edit_tel = st.text_input("Teléfono:", str(fila_cli.get('telefono', ''))).strip()
                    with e_col2:
                        edit_email = st.text_input("E-mail:", str(fila_cli.get('email', ''))).strip().lower()
                        edit_dir = st.text_input("Dirección:", str(fila_cli.get('direccion', ''))).strip()

                    btn_guardar_edit = st.form_submit_button("🔄 Actualizar Datos", use_container_width=True)

                    if btn_guardar_edit:
                        if not edit_nombre: st.error("El nombre no puede estar vacío.")
                        elif edit_tel and (not edit_tel.isdigit() or len(edit_tel) != 10): st.error("El teléfono debe constar de 10 dígitos.")
                        elif edit_email and ("@" not in edit_email or "." not in edit_email): st.error("E-mail no válido.")
                        else:
                            datos_actualizados = {"nombre_razon": edit_nombre, "telefono": edit_tel, "email": edit_email, "direccion": edit_dir}
                            if guardar_registro("clientes", datos_actualizados, "nombre_razon"):
                                st.success("¡Cliente actualizado correctamente!")
                                time.sleep(0.4)
                                st.rerun()

            with st.expander(f"⚠️ Eliminar Registro de {cli_sel}"):
                st.warning("Esta acción borrará al cliente del catálogo permanentemente.")
                chk_confirmar = st.checkbox("Entiendo los riesgos y deseo eliminar este cliente.", key=f"chk_del_{cli_sel}")
                
                if st.button("🗑️ Eliminar Definitivamente", key=f"btn_del_cli_{cli_sel}", use_container_width=True, type="primary"):
                    if not chk_confirmar:
                        st.error("❌ Por favor marca la casilla de confirmación primero.")
                    else:
                        if eliminar_registro("clientes", "nombre_razon", cli_sel):
                            st.success(f"Cliente '{cli_sel}' eliminado.")
                            time.sleep(0.4)
                            st.rerun()

# ==========================================
# MÓDULO 4: PROVEEDORES
# ==========================================
elif modulo_activo == "🚜 Proveedores":
    st.header("🚜 Gestión y Catálogo de Proveedores")
    
    cols_requeridas = ["nombre_proveedor", "insumo_principal", "telefono", "correo", "direccion", "dias_credito", "datos_bancarios", "estatus"]
    
    if df_proveedores.empty:
        df_prov_base = pd.DataFrame(columns=cols_requeridas)
    else:
        df_prov_base = df_proveedores.copy()
        for col in cols_requeridas:
            if col not in df_prov_base.columns:
                df_prov_base[col] = "ACTIVO" if col == "estatus" else ""

    tab_formulario, tab_catalogo = st.tabs(["📝 Formulario de Registro / Edición", "📋 Directorio y Catálogo"])

    with tab_formulario:
        st.subheader("Acción a realizar")
        accion_form = st.radio("Selecciona una opción:", ["➕ Registrar Nuevo Proveedor", "✏️ Modificar Proveedor Existente"], horizontal=True)
        
        es_edicion = accion_form == "✏️ Modificar Proveedor Existente"
        prov_a_editar = None
        datos_previos = {}

        if es_edicion:
            lista_provs = sorted([p for p in df_prov_base["nombre_proveedor"].dropna().unique() if str(p).strip()])
            if lista_provs:
                prov_a_editar = st.selectbox("🔍 Selecciona el proveedor que deseas modificar:", lista_provs)
                registro = df_prov_base[df_prov_base["nombre_proveedor"] == prov_a_editar]
                if not registro.empty:
                    datos_previos = registro.iloc[0].to_dict()
            else:
                st.warning("⚠️ No hay proveedores registrados para modificar.")

        st.markdown("---")
        with st.form("form_proveedores", clear_on_submit=False):
            st.markdown(f"### {'✏️ Modificando: ' + str(prov_a_editar) if es_edicion else '➕ Captura de Nuevo Proveedor'}")
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                p_nombre = st.text_input("Nombre del Proveedor / Razón Social *", value=datos_previos.get("nombre_proveedor", ""), disabled=es_edicion).strip().upper()
                p_insumo = st.text_input("Insumo Principal / Giro *", value=str(datos_previos.get("insumo_principal", ""))).strip().upper()
                
                tel_default = datos_previos.get("telefono", "")
                if not tel_default or str(tel_default).strip() in ["", "None", "nan"]:
                    tel_default = datos_previos.get("contacto", "")
                
                p_telefono = st.text_input("Teléfono de Contacto", value=str(tel_default if str(tel_default) != "None" else "")).strip()
                p_correo = st.text_input("Correo Electrónico", value=str(datos_previos.get("correo", "") if str(datos_previos.get("correo", "")) != "None" else "")).strip()

            with col_f2:
                p_direccion = st.text_input("Dirección / Ubicación", value=str(datos_previos.get("direccion", "") if str(datos_previos.get("direccion", "")) != "None" else "")).strip().upper()
                p_dias_credito = st.number_input("Días de Crédito (0 = Contado)", min_value=0, max_value=120, value=int(datos_previos.get("dias_credito", 0)) if str(datos_previos.get("dias_credito", "0")).isdigit() else 0)
                
                estatus_opciones = ["ACTIVO", "INACTIVO"]
                est_prev = str(datos_previos.get("estatus", "ACTIVO")).upper()
                idx_est = estatus_opciones.index(est_prev) if est_prev in estatus_opciones else 0
                p_estatus = st.selectbox("Estatus", estatus_opciones, index=idx_est)
                
                p_datos_bancarios = st.text_area("Datos de Pago / Cuenta CLABE / Banco", value=str(datos_previos.get("datos_bancarios", "") if str(datos_previos.get("datos_bancarios", "")) != "None" else ""), height=68).strip().upper()

            submit_label = "🔄 Actualizar Proveedor" if es_edicion else "💾 Guardar Proveedor"
            submit_prov = st.form_submit_button(submit_label, use_container_width=True)

            if submit_prov:
                nombre_final = prov_a_editar if es_edicion else p_nombre
                
                if not nombre_final: st.error("❌ El nombre del proveedor es obligatorio.")
                elif not p_insumo: st.error("❌ El insumo principal o giro es obligatorio.")
                else:
                    datos_proveedor = {
                        "nombre_proveedor": nombre_final,
                        "insumo_principal": p_insumo,
                        "telefono": p_telefono,
                        "correo": p_correo,
                        "direccion": p_direccion,
                        "dias_credito": p_dias_credito,
                        "datos_bancarios": p_datos_bancarios,
                        "estatus": p_estatus
                    }
                    if guardar_registro("proveedores", datos_proveedor, "nombre_proveedor"):
                        st.success(f"Proveedor '{nombre_final}' {'actualizado' if es_edicion else 'guardado'} correctamente.")
                        time.sleep(0.4)
                        st.rerun()

    with tab_catalogo:
        st.subheader("📋 Directorio de Proveedores")
        col_bus, col_rep = st.columns([3, 1.5])
        
        with col_bus:
            buscar_prov = st.text_input("🔍 Buscar por Nombre, Insumo, Dirección o Teléfono:", key="bus_prov").strip()

        if not df_prov_base.empty:
            df_prov_vista = df_prov_base.copy()

            if 'contacto' in df_prov_vista.columns:
                df_prov_vista['telefono'] = df_prov_vista['telefono'].replace(['', 'None', 'nan', None], pd.NA)
                df_prov_vista['telefono'] = df_prov_vista['telefono'].fillna(df_prov_vista['contacto'])

            df_prov_vista = df_prov_vista.fillna('-').replace(['', 'None', 'none', 'nan', 'NaN'], '-')
            cols_deseadas = ["nombre_proveedor", "insumo_principal", "telefono", "correo", "direccion", "dias_credito", "datos_bancarios", "estatus"]
            df_prov_vista = df_prov_vista[[c for c in cols_deseadas if c in df_prov_vista.columns]]

            if buscar_prov:
                df_prov_vista = df_prov_vista[df_prov_vista.astype(str).apply(lambda x: x.str.contains(buscar_prov, case=False)).any(axis=1)]

            with col_rep:
                st.write("")
                cols_html_headers = ["Nombre Proveedor", "Insumo Principal", "Teléfono", "Correo", "Dirección", "Días Crédito", "Datos Pago", "Estatus"]
                cols_df_keys = ["nombre_proveedor", "insumo_principal", "telefono", "correo", "direccion", "dias_credito", "datos_bancarios", "estatus"]
                
                cols_existentes_keys = [c for c in cols_df_keys if c in df_prov_vista.columns]
                cols_existentes_headers = [cols_html_headers[i] for i, c in enumerate(cols_df_keys) if c in df_prov_vista.columns]

                html_prov = generar_html_docs("Registro de Proveedores", cols_existentes_headers, df_prov_vista, cols_existentes_keys)
                st.download_button(label="📄 Exportar Reporte (Docs)", data=html_prov, file_name=f"Reporte_Proveedores_{datetime.now().strftime('%Y%m%d')}.doc", mime="application/msword", use_container_width=True)

            st.dataframe(
                df_prov_vista,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "nombre_proveedor": "Proveedor / Razón Social",
                    "insumo_principal": "Insumo Principal / Giro",
                    "telefono": "Teléfono",
                    "correo": "Correo Electrónico",
                    "direccion": "Dirección",
                    "dias_credito": st.column_config.NumberColumn("Días Crédito", format="%d días"),
                    "datos_bancarios": "Datos de Pago",
                    "estatus": "Estatus"
                }
            )

            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🗑️ Eliminar Registro de Proveedor"):
                col_del1, col_del2 = st.columns([3, 1])
                with col_del1:
                    prov_sel_del = st.selectbox("Selecciona Proveedor a Eliminar:", df_prov_base['nombre_proveedor'].unique(), key="sb_del_prov")
                with col_del2:
                    st.write("")
                    if st.button("🗑️ Eliminar Definitivamente", type="primary", use_container_width=True):
                        if eliminar_registro("proveedores", "nombre_proveedor", prov_sel_del):
                            st.success(f"Proveedor '{prov_sel_del}' eliminado correctamente.")
                            time.sleep(0.4)
                            st.rerun()
        else:
            st.info("No hay proveedores registrados aún o no coinciden con la búsqueda.")

# ==========================================
# MÓDULO 5: CONTROL DE LOTES
# ==========================================
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
