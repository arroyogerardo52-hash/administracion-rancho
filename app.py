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
# 3. BARRA LATERAL (Solo visible si ya inició sesión)
# -------------------------------------------------------------
with st.sidebar:
    st.write(f"👤 Hola, **{st.session_state.usuario_actual.capitalize()}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        cerrar_sesion()

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA Y SUPABASE
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

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
# FUNCIONES AUXILIARES Y REPORTES HTML
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
        <p style='margin-top:40px; font-size:11px; color:#999; text-align: center; border-top: 1px dashed #ccc; padding-top: 10px;'>Documento administrativo confidencial generado por el Sistema de Control Interno Rancho AE.</p>
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
            .pnl-table td {{ padding: 8px; border-bottom: 1px solid #E2E8F0; }}
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
    </body>
    </html>
    """
    return html

# ==========================================
# MÓDULO 1: DASHBOARD Y FINANZAS
# ==========================================
if modulo_activo == "📊 Dashboard & Finanzas":
    st.header("📊 Balance y Control General Financiero")

    st.markdown("""
        <style>
        div[data-testid="stMetricValue"] {
            font-size: calc(1rem + 0.6vw) !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        </style>
    """, unsafe_allow_html=True)

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
                        st.markdown("#### 🟢 Cuentas por Cobrar")
                        if not df_vencidos_cobrar.empty:
                            tot_vencido_cob = df_vencidos_cobrar['saldo_pendiente'].sum()
                            st.warning(f"⚠️ **{len(df_vencidos_cobrar)} cobros vencidos** ($ {tot_vencido_cob:,.2f} MXN).")
                            st.dataframe(df_vencidos_cobrar[['id', 'fecha_vencimiento', 'concepto', 'monto', 'abono_acumulado', 'saldo_pendiente']], use_container_width=True)
                        else:
                            st.success("Sin cobros vencidos.")
                            
                    with col_al2:
                        st.markdown("#### 🔴 Cuentas por Pagar")
                        if not df_vencidos_pagar.empty:
                            tot_vencido_pag = df_vencidos_pagar['saldo_pendiente'].sum()
                            st.error(f"⚠️ **{len(df_vencidos_pagar)} deudas vencidas** ($ {tot_vencido_pag:,.2f} MXN).")
                            st.dataframe(df_vencidos_pagar[['id', 'fecha_vencimiento', 'concepto', 'monto', 'abono_acumulado', 'saldo_pendiente']], use_container_width=True)
                        else:
                            st.success("Sin deudas vencidas.")

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
                rango_fechas = st.date_input("Rango de fechas:", [fecha_defecto_inicio, fecha_defecto_fin])
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

        tab_resumen, tab_abonos, tab_graficas, tab_rentabilidad = st.tabs([
            "📋 Resumen Numérico", "💵 Gestión de Abonos y Créditos", "📈 Análisis Gráfico", "📊 Estados Financieros"
        ])
        
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
                st.subheader("📋 Transacciones Seleccionadas")
            with col_btn_rep_filtrado:
                if not df_filtrado.empty:
                    html_profesional_finanzas = generar_reporte_finanzas_profesional(df_filtrado, periodo, lote_seleccionado, ingresos, egresos, balance_neto, por_cobrar, por_pagar)
                    st.download_button("📄 Exportar Reporte (Docs)", html_profesional_finanzas, f"Reporte_Finanzas_{periodo.replace(' ', '_')}.doc", "application/msword", use_container_width=True)
            
            buscar_bal = st.text_input("🔍 Buscar transacción:", key="bus_bal").strip()
            df_bal_vista = df_filtrado.copy()
            if buscar_bal:
                df_bal_vista = df_bal_vista[df_bal_vista.astype(str).apply(lambda x: x.str.contains(buscar_bal, case=False)).any(axis=1)]
                
            if not df_bal_vista.empty:
                df_bal_vista['fecha'] = df_bal_vista['fecha'].dt.strftime('%Y-%m-%d')
                df_bal_estilizado = df_bal_vista.style.apply(colorear_filas_finanzas, axis=1).format({'monto': '$ {:,.2f} MXN', 'abono_acumulado': '$ {:,.2f} MXN'})
                st.dataframe(df_bal_estilizado, use_container_width=True)
            else:
                st.info("Sin registros.")

        with tab_abonos:
            st.subheader("💵 Realizar Abonos a Cuentas Pendientes y Préstamos")
            df_cuentas_abono = df_finanzas[df_finanzas['estado_deuda'] == 'Pendiente'].copy()
            if not df_cuentas_abono.empty:
                df_cuentas_abono['saldo_restante'] = df_cuentas_abono['monto'] - df_cuentas_abono['abono_acumulado']
                df_cuentas_abono = df_cuentas_abono[df_cuentas_abono['saldo_restante'] > 0]

            if not df_cuentas_abono.empty:
                df_cuentas_abono['opcion_texto'] = df_cuentas_abono.apply(lambda x: f"[{x['id']}] {x['tipo'].upper()} | {x['concepto']} | Total: ${x['monto']:,.2f} | Resta: ${x['saldo_restante']:,.2f} MXN", axis=1)
                asig_sel_texto = st.selectbox("Selecciona transacción a abonar:", df_cuentas_abono['opcion_texto'].tolist(), key="sel_abono_cuenta")
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
                    metodo_pago_abono = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque"], key="met_pago_abono")

                with col_ab3:
                    fecha_abono = st.date_input("Fecha del Abono", datetime.today(), key="fec_abono_usr").strftime('%Y-%m-%d')
                    concepto_abono = st.text_input("Nota del Abono", value=f"Abono a {fila_abono['concepto']}", key="con_abono_usr")

                if st.button("💳 Registrar Abono", use_container_width=True, type="primary"):
                    nuevo_abono_acumulado = float(fila_abono['abono_acumulado']) + float(monto_abono)
                    nuevo_estado = "Pagado" if nuevo_abono_acumulado >= float(fila_abono['monto']) else "Pendiente"
                    
                    registro_padre_actualizado = {
                        "id": fila_abono['id'],
                        "fecha": str(fila_abono['fecha'])[:10],
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
                        "fecha_vencimiento": str(fila_abono.get('fecha_vencimiento', ''))[:10]
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
                        st.success(f"¡Abono de $ {monto_abono:,.2f} MXN registrado!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("🎉 Sin cuentas ni préstamos pendientes.")

        with tab_graficas:
            st.subheader("📊 Visualización de Rendimiento")
            if not df_filtrado.empty:
                cg1, cg2 = st.columns(2)
                with cg1:
                    st.write("### 💰 Ingresos vs Egresos Reales")
                    df_pie = df_filtrado[df_filtrado['estado_deuda'] == 'Pagado'].groupby('tipo')['monto'].sum().reset_index()
                    if not df_pie.empty:
                        st.bar_chart(data=df_pie, x='tipo', y='monto', color='tipo', use_container_width=True)
                with cg2:
                    st.write("### 📌 Flujo por Categoría")
                    col_cat = 'categoria' if 'categoria' in df_filtrado.columns else 'tipo'
                    df_cat = df_filtrado.groupby([col_cat, 'tipo'])['monto'].sum().unstack().fillna(0.0)
                    st.bar_chart(df_cat, use_container_width=True)
            else:
                st.info("Sin datos para graficar.")

        with tab_rentabilidad:
            st.subheader("📊 Estado de Resultados (P&L) y Rentabilidad")
            df_pagados = df_filtrado[(df_filtrado['estado_deuda'] == 'Pagado') & (df_filtrado['categoria'] != 'Préstamo / Crédito recibido')].copy()
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
                k1.metric("1️⃣ Flujo Caja Total", f"$ {flujo_caja:,.2f} MXN")
                k2.metric("2️⃣ Utilidad Bruta", f"$ {utilidad_bruta:,.2f} MXN")
                k3.metric("3️⃣ Margen Bruto", f"{margen_bruto:.1f}%")
                k4.metric("4️⃣ Margen Neto", f"{margen_neto:.1f}%")

    st.markdown("---")
    st.subheader("💳 Captura y Registro Financiero")
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
                f_asociado = st.selectbox("Cliente / Origen", lista_clientes, index=0, key="f_cli_pos")
                etiqueta_asociado = "Cliente"
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

        btn_pre_guardar = st.button("Confirmar", use_container_width=True, type="primary")

    if btn_pre_guardar:
        if f_monto <= 0 or not f_concepto:
            st.error("❌ Completa un concepto válido y un monto mayor a $0.00.")
        else:
            st.session_state["transaccion_pendiente"] = {
                "id": f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}",
                "fecha": f_fecha, "tipo": f_tipo_dinamico, "categoria": f_cat, "concepto": f_concepto,
                "monto": float(f_monto), "abono_acumulado": 0.0, "metodo_pago": f_pago, "asociado": f_asociado,
                "etiqueta_asociado": etiqueta_asociado, "lote_asociado": f_lote, "estado_deuda": f_estado,
                "fecha_vencimiento": f_venc, "es_edicion": False
            }

    if "transaccion_pendiente" in st.session_state:
        tx = st.session_state["transaccion_pendiente"]
        with st.expander("👤 **SELECCIONAR EMPLEADO RESPONSABLE**", expanded=True):
            st.info(f"**{tx['tipo']}** de **$ {tx['monto']:,.2f} MXN** - *{tx['concepto']}*")
            opciones_modal_emp = ["-- Seleccionar Empleado --"] + lista_empleados
            emp_seleccionado = st.selectbox("Empleado Responsable *", opciones_modal_emp)
            
            c_exp1, c_exp2 = st.columns(2)
            with c_exp1:
                if st.button("✅ Confirmar y Guardar", disabled=(emp_seleccionado == "-- Seleccionar Empleado --"), use_container_width=True, type="primary"):
                    reg_final = {
                        "id": tx["id"], "fecha": tx["fecha"], "tipo": tx["tipo"], "categoria": tx["categoria"],
                        "concepto": tx["concepto"], "monto": tx["monto"], "abono_acumulado": tx["abono_acumulado"],
                        "metodo_pago": tx["metodo_pago"], "asociado": tx["asociado"], "empleado_responsable": emp_seleccionado,
                        "lote_asociado": tx["lote_asociado"], "estado_deuda": tx["estado_deuda"], "fecha_vencimiento": tx["fecha_vencimiento"]
                    }
                    if guardar_registro("finanzas", reg_final, "id"):
                        st.success("¡Transacción registrada exitosamente!")
                        del st.session_state["transaccion_pendiente"]
                        time.sleep(0.5)
                        st.rerun()
            with c_exp2:
                if st.button("❌ Cancelar", use_container_width=True):
                    del st.session_state["transaccion_pendiente"]
                    st.rerun()

# ==========================================
# MÓDULO 2: EMPLEADOS
# ==========================================
elif modulo_activo == "🤠 Personal / Empleados":
    st.header("🤠 Administración de Personal y Empleados")
    tab_registro, tab_listado, tab_transacciones = st.tabs(["➕ Registrar / Editar Empleado", "📋 Listado de Personal", "📊 Historial de Transacciones"])

    with tab_registro:
        modo_form = st.radio("Acción:", ["Registrar Nuevo Empleado", "Editar Empleado Existente"], horizontal=True)
        e_nombre_val, e_puesto_val, e_sueldo_val = "", "", 0.0
        e_fecha_val, e_periodo_val, e_direccion_val, e_tel_val, e_email_val, e_estatus_val = datetime.today(), "Quincenal", "", "", "Activo"
        
        df_emp_ref = globals().get('df_empleados', pd.DataFrame())

        if modo_form == "Editar Empleado Existente" and not df_emp_ref.empty and 'nombre' in df_emp_ref.columns:
            lista_emp = [e for e in df_emp_ref['nombre'].dropna().unique() if str(e).strip()]
            if lista_emp:
                emp_sel = st.selectbox("Selecciona Empleado:", lista_emp)
                row_e = df_emp_ref[df_emp_ref['nombre'] == emp_sel].iloc[0]
                e_nombre_val, e_puesto_val = str(row_e.get('nombre', '')), str(row_e.get('puesto_funcion', ''))
                e_sueldo_val = float(row_e.get('sueldo', 0.0))
                e_periodo_val, e_tel_val = str(row_e.get('periodo_nomina', 'Quincenal')), str(row_e.get('telefono', ''))
                e_email_val, e_direccion_val = str(row_e.get('email', '')), str(row_e.get('direccion', ''))

        with st.form("form_empleados"):
            c1, c2 = st.columns(2)
            with c1:
                e_nom = st.text_input("Nombre Completo *", value=e_nombre_val).strip().upper()
                e_pue = st.text_input("Puesto / Función", value=e_puesto_val).strip().upper()
                e_sue = st.number_input("Sueldo ($ MXN)", min_value=0.0, value=e_sueldo_val, step=100.0)
                e_fec = st.date_input("Fecha de Contratación", value=e_fecha_val)
                e_per = st.selectbox("Periodo de Nómina", ["Semanal", "Catorcenal", "Quincenal", "Mensual"], index=2)
            with c2:
                e_tel = st.text_input("Teléfono (10 dígitos)", value=e_tel_val).strip()
                e_ema = st.text_input("Correo Electrónico", value=e_email_val).strip().lower()
                e_dir = st.text_area("Dirección", value=e_direccion_val, height=80).strip().upper()
                e_est = st.selectbox("Estatus", ["Activo", "Inactivo"], index=0 if e_estatus_val == "Activo" else 1)

            if st.form_submit_button("💾 Guardar Empleado", use_container_width=True):
                if not e_nom:
                    st.error("❌ El nombre es obligatorio.")
                else:
                    datos_e = {
                        "nombre": e_nom, "puesto_funcion": e_pue, "sueldo": e_sue,
                        "fecha_ingreso": e_fec.strftime('%Y-%m-%d'), "periodo_nomina": e_per,
                        "telefono": e_tel, "email": e_ema, "direccion": e_dir, "estatus": e_est
                    }
                    if guardar_registro("empleados", datos_e, "nombre"):
                        st.success("¡Empleado guardado con éxito!")
                        time.sleep(0.4)
                        st.rerun()

    with tab_listado:
        if not df_empleados.empty:
            st.dataframe(df_empleados, use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros de empleados.")

    with tab_transacciones:
        if not df_finanzas.empty and 'empleado_responsable' in df_finanzas.columns:
            st.dataframe(df_finanzas[['fecha', 'empleado_responsable', 'tipo', 'concepto', 'monto']], use_container_width=True)

# ==========================================
# MÓDULO 3: CLIENTES
# ==========================================
elif modulo_activo == "🤝 Clientes":
    st.header("🤝 Registro y Catálogo de Clientes")
    
    with st.expander("➕ **Registrar Nuevo Cliente**", expanded=True):
        with st.form("form_clientes", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                c_nombre = st.text_input("Razón Social / Nombre *").strip().upper()
                c_tel = st.text_input("Teléfono (10 dígitos)").strip()
            with col_f2:
                c_email = st.text_input("Correo Electrónico").strip().lower()
                c_dir = st.text_input("Dirección / Ubicación").strip()

            if st.form_submit_button("💾 Guardar Cliente", use_container_width=True):
                if not c_nombre:
                    st.error("❌ Nombre obligatorio.")
                else:
                    d_cli = {"nombre_razon": c_nombre, "telefono": c_tel, "email": c_email, "direccion": c_dir}
                    if guardar_registro("clientes", d_cli, "nombre_razon"):
                        st.success("¡Cliente registrado!")
                        time.sleep(0.4)
                        st.rerun()

    st.markdown("### 📋 Catálogo de Clientes")
    if not df_clientes.empty:
        st.dataframe(df_clientes, use_container_width=True, hide_index=True)

# ==========================================
# MÓDULO 4: PROVEEDORES
# ==========================================
elif modulo_activo == "🚜 Proveedores":
    st.header("🚜 Gestión y Catálogo de Proveedores")
    
    cols_requeridas = ["nombre_proveedor", "insumo_principal", "telefono", "correo", "direccion", "dias_credito", "datos_bancarios", "estatus"]
    df_prov_base = df_proveedores.copy() if not df_proveedores.empty else pd.DataFrame(columns=cols_requeridas)
    
    for col in cols_requeridas:
        if col not in df_prov_base.columns:
            df_prov_base[col] = "ACTIVO" if col == "estatus" else ""

    tab_formulario, tab_catalogo = st.tabs(["📝 Formulario de Registro / Edición", "📋 Directorio y Catálogo"])

    with tab_formulario:
        accion_form = st.radio("Selecciona opción:", ["➕ Registrar Nuevo Proveedor", "✏️ Modificar Proveedor Existente"], horizontal=True)
        es_edicion = accion_form == "✏️ Modificar Proveedor Existente"
        prov_a_editar = None
        datos_previos = {}

        if es_edicion:
            lista_provs = sorted([p for p in df_prov_base["nombre_proveedor"].dropna().unique() if str(p).strip()])
            if lista_provs:
                prov_a_editar = st.selectbox("🔍 Selecciona proveedor a modificar:", lista_provs)
                reg_p = df_prov_base[df_prov_base["nombre_proveedor"] == prov_a_editar]
                if not reg_p.empty:
                    datos_previos = reg_p.iloc[0].to_dict()

        with st.form("form_proveedores"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                p_nombre = st.text_input("Nombre del Proveedor / Razón Social *", value=datos_previos.get("nombre_proveedor", ""), disabled=es_edicion).strip().upper()
                p_insumo = st.text_input("Insumo Principal * (Ej: ALIMENTO, MEDICINA)", value=str(datos_previos.get("insumo_principal", ""))).strip().upper()
                p_telefono = st.text_input("Teléfono de Contacto", value=str(datos_previos.get("telefono", ""))).strip()
                p_correo = st.text_input("Correo Electrónico", value=str(datos_previos.get("correo", ""))).strip()

            with col_f2:
                p_direccion = st.text_input("Dirección", value=str(datos_previos.get("direccion", ""))).strip().upper()
                p_dias_credito = st.number_input("Días de Crédito", min_value=0, max_value=120, value=int(datos_previos.get("dias_credito", 0)))
                p_estatus = st.selectbox("Estatus", ["ACTIVO", "INACTIVO"], index=0)
                p_datos_bancarios = st.text_area("Datos de Pago / Cuenta CLABE", value=str(datos_previos.get("datos_bancarios", ""))).strip().upper()

            if st.form_submit_button("💾 Guardar Proveedor", use_container_width=True):
                nombre_final = prov_a_editar if es_edicion else p_nombre
                if not nombre_final or not p_insumo:
                    st.error("❌ Nombre e insumo principal son requeridos.")
                else:
                    d_prov = {
                        "nombre_proveedor": nombre_final, "insumo_principal": p_insumo,
                        "telefono": p_telefono, "correo": p_correo, "direccion": p_direccion,
                        "dias_credito": p_dias_credito, "datos_bancarios": p_datos_bancarios, "estatus": p_estatus
                    }
                    if guardar_registro("proveedores", d_prov, "nombre_proveedor"):
                        st.success(f"Proveedor '{nombre_final}' guardado exitosamente.")
                        time.sleep(0.4)
                        st.rerun()

    with tab_catalogo:
        st.subheader("📋 Directorio de Proveedores")
        col_bus, col_rep = st.columns([3, 1.5])
        with col_bus:
            buscar_prov = st.text_input("🔍 Buscar proveedor:", key="bus_prov").strip()

        if not df_prov_base.empty:
            df_prov_vista = df_prov_base.copy()
            if buscar_prov:
                df_prov_vista = df_prov_vista[df_prov_vista.astype(str).apply(lambda x: x.str.contains(buscar_prov, case=False)).any(axis=1)]

            with col_rep:
                html_prov = generar_html_docs("Catálogo de Proveedores", ["Nombre", "Insumo", "Teléfono", "Correo", "Dirección", "Crédito (Días)", "Estatus"], df_prov_vista, ["nombre_proveedor", "insumo_principal", "telefono", "correo", "direccion", "dias_credito", "estatus"])
                st.download_button("📄 Reporte (Docs)", html_prov, f"Reporte_Proveedores_{datetime.now().strftime('%Y%m%d')}.doc", "application/msword", use_container_width=True)

            st.dataframe(df_prov_vista[cols_requeridas], use_container_width=True, hide_index=True)

# ==========================================
# MÓDULO 5: CONTROL DE LOTES
# ==========================================
elif modulo_activo == "🐂 Control de Lotes":
    st.header("🐂 Administración y Control de Lotes de Ganado")
    
    tab_lotes_reg, tab_lotes_cat, tab_lotes_fin = st.tabs([
        "➕ Captura / Edición de Lote",
        "📋 Catálogo General de Lotes",
        "💰 Historial Financiero por Lote"
    ])

    with tab_lotes_reg:
        modo_lote = st.radio("Acción:", ["Crear Nuevo Lote", "Editar Lote Existente"], horizontal=True)
        l_nombre_val, l_raza_val, l_num_val, l_peso_val = "", "Sardo Negro", 1, 0.0
        l_fec_val, l_est_val, l_obs_val = datetime.today(), "Activo", ""

        if modo_lote == "Editar Lote Existente" and not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
            lista_lotes_opt = [l for l in df_lotes['nombre_lote'].dropna().unique() if str(l).strip()]
            if lista_lotes_opt:
                lote_sel = st.selectbox("Selecciona Lote a Modificar:", lista_lotes_opt)
                row_l = df_lotes[df_lotes['nombre_lote'] == lote_sel].iloc[0]
                l_nombre_val = str(row_l.get('nombre_lote', ''))
                l_raza_val = str(row_l.get('raza_tipo', 'Sardo Negro'))
                l_num_val = int(row_l.get('num_cabezas', 1))
                l_peso_val = float(row_l.get('peso_promedio', 0.0))
                l_est_val = str(row_l.get('estatus', 'Activo'))
                l_obs_val = str(row_l.get('observaciones', ''))

        with st.form("form_lotes"):
            st.subheader("Datos de Identificación del Lote")
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                l_nombre = st.text_input("Nombre / Código de Lote *", value=l_nombre_val, disabled=(modo_lote == "Editar Lote Existente")).strip().upper()
                l_raza = st.selectbox("Raza / Propósito Principal", ["Sardo Negro", "Suiz-Bu", "Comercial / Engorda", "Mestizo / Varios"], index=0)
                l_cabezas = st.number_input("Número de Cabezas", min_value=1, step=1, value=l_num_val)
                l_fecha = st.date_input("Fecha de Creación / Entrada", value=l_fec_val)

            with col_l2:
                l_peso = st.number_input("Peso Promedio Estimado (kg)", min_value=0.0, step=5.0, value=l_peso_val)
                l_estatus = st.selectbox("Estado del Lote", ["Activo", "Vendido / Cerrado", "En Transición"], index=0 if l_est_val == "Activo" else 1)
                l_obs = st.text_area("Observaciones o Ubicación de Pastoreo", value=l_obs_val, height=80).strip()

            if st.form_submit_button("💾 Guardar Lote", use_container_width=True):
                nombre_lote_final = lote_sel if modo_lote == "Editar Lote Existente" else l_nombre
                if not nombre_lote_final:
                    st.error("❌ El nombre de lote es obligatorio.")
                else:
                    datos_lote = {
                        "nombre_lote": nombre_lote_final,
                        "raza_tipo": l_raza,
                        "num_cabezas": l_cabezas,
                        "fecha_ingreso": l_fecha.strftime('%Y-%m-%d'),
                        "peso_promedio": l_peso,
                        "estatus": l_estatus,
                        "observaciones": l_obs
                    }
                    if guardar_registro("lotes", datos_lote, "nombre_lote"):
                        st.success(f"¡Lote '{nombre_lote_final}' procesado correctamente!")
                        time.sleep(0.4)
                        st.rerun()

    with tab_lotes_cat:
        st.subheader("📋 Lotes Registrados en Rancho AE")
        if not df_lotes.empty:
            st.dataframe(df_lotes, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🗑️ Eliminar Lote")
            col_dl1, col_dl2 = st.columns([3, 1])
            with col_dl1:
                lote_elim_sel = st.selectbox("Selecciona Lote a Eliminar:", df_lotes['nombre_lote'].unique(), key="sb_del_lote")
            with col_dl2:
                st.write("###")
                if st.button("🗑️ Eliminar Lote", type="primary", use_container_width=True):
                    if eliminar_registro("lotes", "nombre_lote", lote_elim_sel):
                        st.success(f"Lote {lote_elim_sel} eliminado.")
                        time.sleep(0.4)
                        st.rerun()
        else:
            st.info("No hay lotes registrados actualmente.")

    with tab_lotes_fin:
        st.subheader("💰 Desglose Contable Vínculado por Lote")
        if not df_lotes.empty and not df_finanzas.empty:
            lote_f_sel = st.selectbox("Ver movimientos del lote:", df_lotes['nombre_lote'].unique(), key="sb_fin_lote")
            df_fin_lote = df_finanzas[df_finanzas['lote_asociado'] == lote_f_sel]
            
            if not df_fin_lote.empty:
                tot_ing_lote = df_fin_lote[df_fin_lote['tipo'] == 'Ingreso']['monto'].sum()
                tot_egr_lote = df_fin_lote[df_fin_lote['tipo'] == 'Egreso']['monto'].sum()
                bal_lote = tot_ing_lote - tot_egr_lote
                
                cl1, cl2, cl3 = st.columns(3)
                cl1.metric("Ingresos Directos", f"$ {tot_ing_lote:,.2f} MXN")
                cl2.metric("Egresos Directos", f"$ {tot_egr_lote:,.2f} MXN")
                cl3.metric("Balance Neto de Lote", f"$ {bal_lote:,.2f} MXN")
                
                st.dataframe(df_fin_lote[['fecha', 'tipo', 'categoria', 'concepto', 'monto', 'estado_deuda']], use_container_width=True)
            else:
                st.info(f"El lote **{lote_f_sel}** no tiene movimientos financieros vinculados.")
        else:
            st.info("Información insuficiente para generar desglose.")
