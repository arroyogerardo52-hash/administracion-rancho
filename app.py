import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import time
import plotly.express as px

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
# FUNCIONES DE ESTILO DE FILAS PARA LOS HISTORIALES
# ==========================================
def colorear_filas_finanzas(row):
    if row['tipo'] == 'Ingreso':
        return ['background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; font-weight: bold;'] * len(row)
    elif row['tipo'] == 'Egreso':
        return ['background-color: rgba(231, 76, 60, 0.12); color: #e74c3c;'] * len(row)
    return [''] * len(row)

# ==========================================
# 4. PANEL DE BALANCE GLOBAL & ESTADÍSTICAS
# ==========================================
st.header("📊 Balance y Control General Financiero")

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
                [fecha_defecto_inicio, fecha_defecto_fin]
            )
            
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

    ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    
    por_cobrar = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    
    tab_resumen, tab_graficas = st.tabs(["📋 Resumen Numérico", "📈 Análisis Gráfico"])
    
    with tab_resumen:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🟢 Ingresos Reales", f"${ingresos:,.2f}")
        m2.metric("🔴 Egresos Reales", f"${egresos:,.2f}")
        m3.metric("💰 Balance Neto", f"${balance_neto:,.2f}", delta=f"${balance_neto:,.2f}" if balance_neto >= 0 else f"${balance_neto:,.2f}", delta_color="normal" if balance_neto >= 0 else "inverse")
        m4.metric("📈 Por Cobrar", f"${por_cobrar:,.2f}")
        m5.metric("📉 Por Pagar", f"${por_pagar:,.2f}")
        
        st.write("---")
        st.subheader("📋 Transacciones del Período")
        
        buscar_bal = st.text_input("🔍 Buscar en las transacciones del período:", key="bus_bal").strip()
        df_bal_vista = df_filtrado.copy()
        
        if buscar_bal and not df_bal_vista.empty:
            mascara = df_bal_vista.astype(str).apply(lambda x: x.str.contains(buscar_bal, case=False)).any(axis=1)
            df_bal_vista = df_bal_vista[mascara]
            
        if not df_bal_vista.empty:
            df_bal_vista['fecha'] = df_bal_vista['fecha'].dt.strftime('%Y-%m-%d')
            df_bal_estilizado = (df_bal_vista.style
                                 .apply(colorear_filas_finanzas, axis=1)
                                 .format({'monto': '${:,.2f}'}))
            st.dataframe(df_bal_estilizado, use_container_width=True)
        else:
            st.info("No hay registros que coincidan con la búsqueda.")

        st.write("### 📄 Exportar Reporte Ejecutivo")
        
        # =========================================================================
        # ESTRUCTURA INTEGRADA DEL NUEVO BLOQUE DE DISEÑO PROFESIONAL
        # =========================================================================
        df_ingresos_cat = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado')].groupby('categoria')['monto'].sum()
        df_egresos_cat = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')].groupby('categoria')['monto'].sum()

        folio_reporte = f"R-AE-{hoy.strftime('%Y%m%d')}-{int(time.time()) % 10000}"
        color_balance = "positive" if balance_neto >= 0 else "negative"

        html_reporte = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2d3748; line-height: 1.6; margin: 30px; }}
                .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; border-bottom: 3px solid #1a365d; }}
                .header-logo {{ width: 30%; text-align: left; padding-bottom: 15px; }}
                .header-title {{ width: 70%; text-align: right; padding-bottom: 15px; }}
                .header-title h1 {{ margin: 0; color: #1a365d; font-size: 26px; text-transform: uppercase; letter-spacing: 1px; }}
                .header-title p {{ margin: 5px 0 0 0; color: #718096; font-size: 13px; }}
                
                .meta-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: #f7fafc; }}
                .meta-table td {{ padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; }}
                .meta-label {{ font-weight: bold; color: #4a5568; background-color: #edf2f7; width: 20%; }}
                
                h2 {{ color: #1a365d; font-size: 14px; margin-top: 35px; margin-bottom: 15px; border-bottom: 1px solid #cbd5e0; padding-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }}
                
                .financial-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 14px; }}
                .financial-table th {{ background-color: #1a365d; color: white; padding: 10px 12px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
                .financial-table td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
                .financial-table tr:nth-child(even) {{ background-color: #f8fafc; }}
                
                .text-right {{ text-align: right; }}
                .text-center {{ text-align: center; }}
                .font-bold {{ font-weight: bold; }}
                
                .row-total {{ background-color: #edf2f7 !important; font-weight: bold; color: #1a365d; }}
                .row-grand-total {{ background-color: #e2e8f0 !important; font-weight: bold; color: #1a365d; font-size: 15px; }}
                .double-underline {{ border-bottom: 4px double #1a365d !important; }}
                
                .positive {{ color: #2f855a; }}
                .negative {{ color: #9b2c2c; }}
                .badge-paid {{ background-color: #c6f6d5; color: #22543d; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
                .badge-pending {{ background-color: #feebc8; color: #744210; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
                
                .footer {{ margin-top: 60px; text-align: center; font-size: 11px; color: #a0aec0; border-top: 1px solid #e2e8f0; padding-top: 15px; }}
                .signature-area {{ width: 100%; margin-top: 50px; border-collapse: collapse; }}
                .signature-box {{ width: 50%; text-align: center; font-size: 13px; padding-top: 40px; }}
                .signature-line {{ width: 60%; margin: 0 auto; border-top: 1px solid #4a5568; padding-top: 5px; }}
            </style>
        </head>
        <body>

            <table class="header-table">
                <tr>
                    <td class="header-logo">
                        <span style="font-size: 24px; font-weight: bold; color: #1a365d;">🤠 RANCHO AE</span>
                    </td>
                    <td class="header-title">
                        <h1>Informe de Situación Financiera</h1>
                        <p>Control Interno de Gestión y Resultados Operativos</p>
                    </td>
                </tr>
            </table>

            <table class="meta-table">
                <tr>
                    <td class="meta-label">Organización:</td>
                    <td>Rancho AE | Genética y Engorda Comercial</td>
                    <td class="meta-label">Folio Reporte:</td>
                    <td class="font-bold">{folio_reporte}</td>
                </tr>
                <tr>
                    <td class="meta-label">Período Contable:</td>
                    <td>{periodo} ({fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')})</td>
                    <td class="meta-label">Fecha de Emisión:</td>
                    <td>{datetime.now().strftime('%d/%m/%Y %H:%M')}</td>
                </tr>
            </table>

            <h2>I. Resumen Ejecutivo de Rendimiento (P&L)</h2>
            <table class="financial-table">
                <thead>
                    <tr>
                        <th style="width: 70%;">Cuenta / Concepto Contable</th>
                        <th style="width: 30%; text-align: right;">Monto Liquidado (MXN)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="font-bold">Ingresos Operativos Totales</td>
                        <td class="text-right positive font-bold">${ingresos:,.2f}</td>
                    </tr>
                    <tr>
                        <td class="font-bold" style="padding-left: 20px; color: #4a5568;">(-) Costos y Gastos Operativos</td>
                        <td class="text-right negative" style="border-bottom: 1px solid #4a5568;">(${egresos:,.2f})</td>
                    </tr>
                    <tr class="row-grand-total">
                        <td>UTILIDAD BRUTA (BALANCE NETO LIQUIDADO)</td>
                        <td class="text-right double-underline {color_balance}">${balance_neto:,.2f}</td>
                    </tr>
                </tbody>
            </table>

            <h2>II. Cuentas Corrientes y Obligaciones Pendientes</h2>
            <table class="financial-table">
                <thead>
                    <tr>
                        <th style="width: 70%;">Rubro de Exigibilidad</th>
                        <th style="width: 30%; text-align: right;">Saldo Proyectado (MXN)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Cuentas por Cobrar (Ingresos en Cartera Pendiente)</td>
                        <td class="text-right" style="color: #2b6cb0;">${por_cobrar:,.2f}</td>
                    </tr>
                    <tr>
                        <td>Cuentas por Pagar (Obligaciones y Compromisos Pendientes)</td>
                        <td class="text-right" style="color: #dd6b20;">${por_pagar:,.2f}</td>
                    </tr>
                    <tr class="row-total">
                        <td class="font-bold">Flujo de Caja Potencial en Cartera</td>
                        <td class="text-right font-bold">${(por_cobrar - por_pagar):,.2f}</td>
                    </tr>
                </tbody>
            </table>

            <h2>III. Análisis de Distribución por Categoría</h2>
            <table class="financial-table">
                <thead>
                    <tr>
                        <th>Categoría / Tipo de Flujo</th>
                        <th>Naturaleza</th>
                        <th class="text-right">Total Acumulado</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for cat, monto in df_ingresos_cat.items():
            html_reporte += f"""
                    <tr>
                        <td>{cat}</td>
                        <td style="color: #2f855a; font-size: 12px;">Ingreso Operativo</td>
                        <td class="text-right positive">${monto:,.2f}</td>
                    </tr>
            """
        for cat, monto in df_egresos_cat.items():
            html_reporte += f"""
                    <tr>
                        <td>{cat}</td>
                        <td style="color: #9b2c2c; font-size: 12px;">Costo / Gasto Operativo</td>
                        <td class="text-right negative">${monto:,.2f}</td>
                    </tr>
            """
            
        html_reporte += f"""
                </tbody>
            </table>

            <h2>IV. Libro Auxiliar de Transacciones Detalladas</h2>
            <table class="financial-table" style="font-size: 12px;">
                <thead>
                    <tr>
                        <th style="width: 12%;">Fecha</th>
                        <th style="width: 15%;">ID Transacción</th>
                        <th style="width: 15%;">Categoría</th>
                        <th style="width: 30%;">Concepto / Descripción</th>
                        <th style="width: 13%; text-align: center;">Estado</th>
                        <th style="width: 15%; text-align: right;">Monto</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for _, fila in df_filtrado.iterrows():
            f_date = fila['fecha'].strftime('%d/%m/%Y') if pd.notnull(fila['fecha']) else ''
            concepto = fila.get('concepto', fila.get('detalle', 'Sin concepto'))
            clase_monto = "positive" if fila['tipo'] == "Ingreso" else "negative"
            prefijo = "" if fila['tipo'] == "Ingreso" else "-"
            
            estado_badge = f"<span class='badge-paid'>PAGADO</span>" if fila['estado_deuda'] == "Pagado" else f"<span class='badge-pending'>PENDIENTE</span>"
            
            html_reporte += f"""
                    <tr>
                        <td class="text-center">{f_date}</td>
                        <td style="color:#718096; font-family: monospace;">{fila['id']}</td>
                        <td class="font-bold">{fila['categoria']}</td>
                        <td>{concepto}</td>
                        <td class="text-center">{estado_badge}</td>
                        <td class="text-right {clase_monto} font-bold">{prefijo}${fila['monto']:,.2f}</td>
                    </tr>
            """
            
        html_reporte += f"""
                </tbody>
            </table>

            <table class="signature-area">
                <tr>
                    <td class="signature-box">
                        <div class="signature-line"></div>
                        <strong>Gerardo Arroyo Espinoza</strong><br>
                        Dirección General / Administración A.E
                    </td>
                    <td class="signature-box">
                        <div class="signature-line"></div>
                        <strong>Control Interno</strong><br>
                        Rancho AE - Auditoría Ganadera
                    </td>
                </tr>
            </table>

            <div class="footer">
                <p>Este documento es un extracto oficial de la base de datos financiera de Rancho AE. Todos los saldos mostrados están sujetos a los criterios de conciliación de caja vigentes.</p>
                <p>© {datetime.now().year} Administracion A.E - Zentla, Veracruz. Todos los derechos reservados.</p>
            </div>
        </body>
        </html>
        """
        
        st.download_button(
            label="📥 Descargar Reporte para Google Docs",
            data=html_reporte,
            file_name=f"Balance_Financiero_{periodo.replace(' ', '_')}_{hoy.strftime('%Y%m%d')}.doc",
            mime="application/msword",
            help="Descarga este archivo y súbelo directamente a tu Google Drive."
        )

    with tab_graficas:
        st.subheader("📊 Visualización de Rendimiento del Período")
        if not df_filtrado.empty:
            cg1, cg2 = st.columns(2)
            df_pie = df_filtrado[df_filtrado['estado_deuda'] == 'Pagado'].groupby('tipo')['monto'].sum().reset_index()
            
            with cg1:
                st.write("### 💰 Ingresos vs Egresos Reales")
                if not df_pie.empty:
                    st.bar_chart(data=df_pie, x='tipo', y='monto', color='tipo', use_container_width=True)
                else:
                    st.info("No hay transacciones pagadas en este rango para graficar.")
            
            with cg2:
                st.write("### 📌 Flujo por Categoría de Gasto/Ingreso")
                col_cat = 'categoria' if 'categoria' in df_filtrado.columns else ('concepto' if 'concepto' in df_filtrado.columns else 'tipo')
                df_cat = df_filtrado.groupby([col_cat, 'tipo'])['monto'].sum().unstack().fillna(0.0)
                st.bar_chart(df_cat, use_container_width=True)
                
            st.write("---")
            col_dona_centrada, _ = st.columns([2, 1])
            with col_dona_centrada:
                st.write("### 🍩 Distribución de Capital")
                if not df_pie.empty:
                    fig_donut = px.pie(
                        df_pie, 
                        values='monto', 
                        names='tipo', 
                        hole=0.6,  
                        color='tipo',
                        color_discrete_map={'Ingreso': '#2ecc71', 'Egreso': '#e74c3c'}  
                    )
                    fig_donut.update_traces(
                        textinfo='percent', 
                        textposition='inside', 
                        insidetextfont=dict(size=14)
                    )
                    fig_donut.update_layout(
                        showlegend=True,
                        margin=dict(t=30, b=25, l=20, r=20),
                        height=350,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_donut, use_container_width=True)
                else:
                    st.info("Faltan movimientos de capital liquidados para calcular la distribución.")
                
            st.write("---")
            st.write("### 📈 Tendencia Financiera Histórica del Período")
            df_linea = df_filtrado.copy()
            df_linea['Fecha'] = df_linea['fecha'].dt.date
            df_tendencia = df_linea.groupby(['Fecha', 'tipo'])['monto'].sum().unstack().fillna(0.0)
            
            if 'Ingreso' not in df_tendencia.columns: df_tendencia['Ingreso'] = 0.0
            if 'Egreso' not in df_tendencia.columns: df_tendencia['Egreso'] = 0.0
            st.line_chart(df_tendencia[['Ingreso', 'Egreso']], use_container_width=True)
        else:
            st.info("Selecciona un período con registros para poder desplegar los análisis gráficos.")
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
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta Animales)").strip().upper()
            f_concepto = st.text_input("Concepto / Descripción").strip()
        with col2:
            f_monto = st.number_input("Monto total ($)", min_value=0.0, step=100.0)
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento", datetime.today()).strftime('%Y-%m-%d')
            
        guardar_fin_btn = st.form_submit_button("💾 Guardar Transacción")
        
    if guardar_fin_btn:
        auto_id = f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}"
        nuevo_registro = {
            "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
            "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
            "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
        }
        if guardar_registro("finanzas", nuevo_registro, "id"):
            st.success(f"¡Transacción registrada con ID simplificado: {auto_id}!")
            st.session_state["mostrar_descarga"] = False
            time.sleep(0.4)
            st.rerun()

    st.markdown("### Historial de Movimientos")
    buscar_fin = st.text_input("🔍 Buscar en Historial de Finanzas:", key="bus_fin").strip()
    
    if not df_finanzas.empty:
        df_vista_finanzas = df_finanzas.copy()
        df_vista_finanzas['fecha'] = df_vista_finanzas['fecha'].dt.strftime('%Y-%m-%d')
        df_vista_finanzas = df_vista_finanzas.reindex(columns=["id", "fecha", "tipo", "categoria", "concepto", "monto", "metodo_pago", "lote_asociado", "estado_deuda", "fecha_vencimiento"])
        
        if buscar_fin:
            mascara = df_vista_finanzas.astype(str).apply(lambda x: x.str.contains(buscar_fin, case=False)).any(axis=1)
            df_vista_finanzas = df_vista_finanzas[mascara]
            
        if not df_vista_finanzas.empty:
            df_fin_estilizado = (df_vista_finanzas.style
                                 .apply(colorear_filas_finanzas, axis=1)
                                 .format({'monto': '${:,.2f}'}))
            st.dataframe(df_fin_estilizado, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron transacciones que coincidan.")

    # Modificar o Eliminar Transacción
    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        id_seleccionado = st.selectbox("Selecciona ID a alterar:", df_finanzas['id'].unique(), key="del_fin")
        fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
        
        fecha_orig_str = fila_sel['fecha'].strftime('%Y-%m-%d') if hasattr(fila_sel['fecha'], 'strftime') else str(fila_sel['fecha'])[:10]
        
        c1, c2, c3 = st.columns([2, 2, 1])
        lista_estados = ["Pagado", "Pendiente"]
        idx_estado = lista_estados.index(fila_sel['estado_deuda']) if fila_sel['estado_deuda'] in lista_estados else 0
        
        with c1:
            nuevo_estado = st.selectbox("Cambiar Estado Pago a:", lista_estados, index=idx_estado, key=f"est_fin_{id_seleccionado}")
        with c2:
            nuevo_monto = st.number_input("Corregir Monto ($):", min_value=0.0, value=float(fila_sel['monto']), step=100.0, key=f"mon_fin_{id_seleccionado}")
        with c3:
            st.write("")
            st.write("")
            
            if st.button("🔄 Actualizar", key=f"btn_up_fin_{id_seleccionado}", use_container_width=True):
                registro_actualizado = {
                    "id": str(id_seleccionado), "fecha": fecha_orig_str, "tipo": str(fila_sel.get('tipo', '')),
                    "categoria": str(fila_sel.get('categoria', '')).strip().upper(), "concepto": str(fila_sel.get('concepto', '')).strip(),
                    "monto": float(nuevo_monto), "metodo_pago": str(fila_sel.get('metodo_pago', '')),
                    "lote_asociado": str(fila_sel.get('lote_asociado', '')), "estado_deuda": str(nuevo_estado),
                    "fecha_vencimiento": str(fila_sel.get('fecha_vencimiento', ''))
                }
                if guardar_registro("finanzas", registro_actualizado, "id"):
                    st.success("¡Registro modificado con éxito!")
                    st.session_state["mostrar_descarga"] = False
                    time.sleep(0.4)
                    st.rerun()
            
            if st.button("🗑️ Eliminar", key=f"btn_del_fin_{id_seleccionado}", use_container_width=True, type="primary"):
                if eliminar_registro("finanzas", "id", id_seleccionado):
                    st.warning("Registro eliminado de la base de datos.")
                    st.session_state["mostrar_descarga"] = False
                    time.sleep(0.4)
                    st.rerun()

# PESTAÑA EMPLEADOS EN ADELANTE (Continuará según la lógica de tu aplicación)...
