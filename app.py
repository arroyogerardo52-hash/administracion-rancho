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
# FUNCIONES PARA GENERAR REPORTES PROFESIONALES (HTML COMPATIBLE CON GOOGLE DOCS)
# ==========================================
def generar_html_docs(titulo_seccion, columnas_headers, df_datos, mapping_columnas):
    hoy_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    html = f"""
    <html>
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
    hoy_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2C3E50; line-height: 1.6; margin: 30px; }}
            .header-table {{ width: 100%; border: none; margin-bottom: 20px; }}
            .header-title {{ font-size: 26px; color: #1A365D; font-weight: bold; margin: 0; }}
            .header-subtitle {{ font-size: 13px; color: #718096; text-transform: uppercase; letter-spacing: 1px; }}
            .divider {{ height: 3px; background-color: #2B6CB0; margin-top: 5px; margin-bottom: 20px; }}
            
            .meta-section {{ background-color: #EDF2F7; padding: 15px; border-radius: 5px; margin-bottom: 25px; font-size: 13px; }}
            .meta-table {{ width: 100%; border-collapse: collapse; }}
            .meta-table td {{ border: none; padding: 4px 0; color: #4A5568; }}
            
            .kpi-container {{ width: 100%; margin-bottom: 30px; }}
            .kpi-box {{ width: 18%; display: inline-block; background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #4A5568; text-align: center; padding: 12px 5px; margin-right: 1%; border-radius: 4px; }}
            .kpi-box.ingreso {{ border-top-color: #2ECC71; }}
            .kpi-box.egreso {{ border-top-color: #E74C3C; }}
            .kpi-box.balance {{ border-top-color: #2B6CB0; }}
            .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #718096; font-weight: bold; margin-bottom: 5px; }}
            .kpi-value {{ font-size: 15px; font-weight: bold; color: #1A365D; }}
            
            .section-title {{ font-size: 18px; color: #2B6CB0; margin-top: 30px; margin-bottom: 10px; font-weight: bold; border-bottom: 1px solid #E2E8F0; padding-bottom: 5px; }}
            
            .data-table {{ border-collapse: collapse; width: 100%; margin-top: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .data-table th {{ background-color: #1A365D; color: white; padding: 10px 8px; text-align: left; font-size: 11px; font-weight: bold; text-transform: uppercase; border: 1px solid #1A365D; }}
            .data-table td {{ border: 1px solid #E2E8F0; padding: 8px; font-size: 11px; color: #2D3748; }}
            .data-table tr:nth-child(even) {{ background-color: #F7FAFC; }}
            
            .text-right {{ text-align: right; }}
            .bold {{ font-weight: bold; }}
            .color-ingreso {{ color: #27AE60; }}
            .color-egreso {{ color: #C0392B; }}
        </style>
    </head>
    <body>
        <table class="header-table">
            <tr>
                <td>
                    <div class="header-title">RANCHO AE</div>
                    <div class="header-subtitle">Estado Ejecutivo de Transacciones y Control Financiero</div>
                </td>
            </tr>
        </table>
        <div class="divider"></div>
        
        <div class="meta-section">
            <table class="meta-table">
                <tr>
                    <td width="20%"><strong>Período Auditado:</strong></td><td width="30%">{periodo}</td>
                    <td width="20%"><strong>Filtro de Lote:</strong></td><td width="30%">{lote}</td>
                </tr>
                <tr>
                    <td><strong>Fecha de Emisión:</strong></td><td>{hoy_str}</td>
                    <td><strong>Estatus del Reporte:</strong></td><td>Cierre de Ciclo Automatizado</td>
                </tr>
            </table>
        </div>
        
        <div class="section-title">Indicadores de Rendimiento Financiero</div>
        <div class="kpi-container">
            <div class="kpi-box ingreso"><div class="kpi-title">Ingresos Reales</div><div class="kpi-value color-ingreso">${ing:,.2f}</div></div>
            <div class="kpi-box egreso"><div class="kpi-title">Egresos Reales</div><div class="kpi-value color-egreso">${egr:,.2f}</div></div>
            <div class="kpi-box balance"><div class="kpi-title">Balance Neto</div><div class="kpi-value">${net:,.2f}</div></div>
            <div class="kpi-box"><div class="kpi-title">Por Cobrar</div><div class="kpi-value" style="color:#2980B9;">${cob:,.2f}</div></div>
            <div class="kpi-box" style="margin-right:0;"><div class="kpi-title">Por Pagar</div><div class="kpi-value" style="color:#D35400;">${pag:,.2f}</div></div>
        </div>
        
        <div class="section-title">Desglose Analítico de Movimientos del Período</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Categoría</th>
                    <th>Concepto / Detalle Informativo</th>
                    <th>Lote</th>
                    <th>Método</th>
                    <th>Estado</th>
                    <th class="text-right">Monto</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, fila in df_datos.iterrows():
        f_date = fila['fecha']
        if hasattr(f_date, 'strftime'):
            f_str = f_date.strftime('%Y-%m-%d')
        else:
            f_str = str(f_date)[:10]
            
        concepto = fila.get('concepto', 'Sin concepto')
        lote_asoc = fila.get('lote_asociado', 'Ninguno')
        tipo_mov = fila.get('tipo', '')
        clase_color = "color-ingreso bold" if tipo_mov == "Ingreso" else "color-egreso"
        
        html += f"""
                <tr>
                    <td>{f_str}</td>
                    <td class="{clase_color}">{tipo_mov}</td>
                    <td>{fila.get('categoria', 'GENERAL')}</td>
                    <td>{concepto}</td>
                    <td>{lote_asoc}</td>
                    <td>{fila.get('metodo_pago', 'No especificado')}</td>
                    <td>{fila.get('estado_deuda', 'Pagado')}</td>
                    <td class="text-right bold {clase_color}">${fila['monto']:,.2f}</td>
                </tr>
        """
        
    html += f"""
                <tr style="background-color: #E2E8F0; font-weight: bold;">
                    <td colspan="7" class="text-right" style="font-size: 12px; padding: 10px;">BALANCE DEL PERÍODO EXPORTADO:</td>
                    <td class="text-right" style="font-size: 12px; padding: 10px; color: {'#27AE60' if net >= 0 else '#C0392B'}">${net:,.2f}</td>
                </tr>
            </tbody>
        </table>
        
        <p style='margin-top:50px; font-size:11px; color:#A0AEC0; text-align: center; border-top: 1px solid #E2E8F0; padding-top: 15px;'>
            Este balance ejecutivo constituye un extracto oficial de la contabilidad interna de Rancho AE. Súbase directamente a Google Drive para su archivo permanente o firmas conducentes.
        </p>
    </body>
    </html>
    """
    return html

# ==========================================
# 4. PANEL DE BALANCE GLOBAL & ESTADÍSTICAS
# ==========================================
st.header("📊 Balance y Control General Financiero")

if not df_finanzas.empty:
    df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
    df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
    df_finanzas = df_finanzas.dropna(subset=['fecha'])
    
    st.subheader("📆 Filtros de Consulta")
    col_filtro, col_lote_filtro, col_fechas = st.columns([2, 2, 3])
    
    hoy = datetime.today()
    fecha_inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_fin = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)

    with col_filtro:
        periodo = st.selectbox(
            "Selecciona el período visualizado:",
            ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"]
        )

    with col_lote_filtro:
        opciones_filtro_lote = ["Todos los Lotes"]
        if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
            opciones_filtro_lote += list(df_lotes['nombre_lote'].dropna().unique())
        lote_seleccionado = st.selectbox("Filtrar por Lote Asociado:", opciones_filtro_lote)

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
                    st.warning("⏳ Por favor, selecciona la fecha de fin en el calendario para actualizar los datos.")
                    fecha_inicio, fecha_fin = None, None
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

    if periodo != "Todo el Historial" and fecha_inicio is not None and fecha_fin is not None:
        f_inicio_pd = pd.to_datetime(fecha_inicio)
        f_fin_pd = pd.to_datetime(fecha_fin)
        df_filtrado = df_filtrado[(df_filtrado['fecha'] >= f_inicio_pd) & (df_filtrado['fecha'] <= f_fin_pd)]

    if lote_seleccionado != "Todos los Lotes" and 'lote_asociado' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['lote_asociado'] == lote_seleccionado]

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
        
        # MÓDULO NUEVO Y REUBICADO: Botón de Reporte Ejecutivo Profesional por Período Filtrado
        col_tit_trans, col_btn_rep_filtrado = st.columns([3, 1])
        with col_tit_trans:
            st.subheader("📋 Transacciones del Período Seleccionado")
        with col_btn_rep_filtrado:
            if not df_filtrado.empty:
                html_profesional_finanzas = generar_reporte_finanzas_profesional(
                    df_filtrado, periodo, lote_seleccionado, ingresos, egresos, balance_neto, por_cobrar, por_pagar
                )
                st.download_button(
                    label="📄 Exportar Reporte de este Período (Docs)",
                    data=html_profesional_finanzas,
                    file_name=f"Reporte_Ejecutivo_Finanzas_{periodo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.doc",
                    mime="application/msword",
                    use_container_width=True,
                    help="Genera un reporte claro y formal listo para importar en Google Drive con las transacciones del filtro actual."
                )
        
        buscar_bal = st.text_input("🔍 Buscar en las transacciones del período:", key="bus_bal").strip()
        df_bal_vista = df_filtrado.copy()
        
        if buscar_bal:
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

    with tab_graficas:
        st.subheader("📊 Visualización de Rendimiento")
        if not df_filtrado.empty:
            cg1, cg2 = st.columns(2)
            with cg1:
                st.write("### 💰 Ingresos vs Egresos Reales")
                df_pie = df_filtrado[df_filtrado['estado_deuda'] == 'Pagado'].groupby('tipo')['monto'].sum().reset_index()
                if not df_pie.empty:
                    st.bar_chart(data=df_pie, x='tipo', y='monto', color='tipo', use_container_width=True)
                else:
                    st.info("No hay transacciones pagadas en este rango para graficar.")
            
            with cg2:
                st.write("### 📌 Flujo por Categoría")
                col_cat = 'categoria' if 'categoria' in df_filtrado.columns else ('concepto' if 'concepto' in df_filtrado.columns else 'tipo')
                df_cat = df_filtrado.groupby([col_cat, 'tipo'])['monto'].sum().unstack().fillna(0.0)
                st.bar_chart(df_cat, use_container_width=True)
                
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

st.markdown("---")

# ==========================================
# 5. PESTAÑAS OPERATIVAS CON BOTONES DE REPORTE INDEPENDIENTES
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# PESTAÑA FINANZAS (¡BOTÓN DE REPORTE REMOVIDO DE AQUÍ COMO FUE SOLICITADO!)
with tabs[0]:
    st.subheader("Registro Financiero Automático")
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_fecha = st.date_input("Fecha Transacción", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta Animales, Medicina)").strip().upper()
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
            
        submit_finanzas = st.form_submit_button("💾 Guardar Transacción")
        if submit_finanzas:
            if f_monto <= 0:
                st.error("❌ El monto debe ser mayor a $0.00 pesos.")
            elif not f_concepto:
                st.error("❌ Por favor escribe un Concepto o Descripción para la transacción.")
            else:
                auto_id = f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}"
                nuevo_registro = {
                    "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat if f_cat else "GENERAL",
                    "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                    "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
                }
                if guardar_registro("finanzas", nuevo_registro, "id"):
                    st.success(f"¡Transacción registrada con ID simplificado: {auto_id}!")
                    time.sleep(0.4)
                    st.rerun()

    st.markdown("### Historial de Movimientos")
    buscar_fin = st.text_input("🔍 Buscar en Historial de Finanzas:", key="bus_fin").strip()
    
    df_vista_finanzas = df_finanzas.copy()
    if not df_vista_finanzas.empty:
        if 'fecha' in df_vista_finanzas.columns:
            df_vista_finanzas['fecha'] = pd.to_datetime(df_vista_finanzas['fecha']).dt.strftime('%Y-%m-%d')
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

    # Edición Manual de Transacciones
    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        id_seleccionado = st.selectbox("Selecciona ID a alterar:", df_finanzas['id'].unique(), key="del_fin")
        fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
        
        try:
            fecha_orig = pd.to_datetime(fila_sel['fecha']).date()
        except:
            fecha_orig = datetime.today().date()
            
        try:
            f_venc_orig = pd.to_datetime(fila_sel.get('fecha_vencimiento', datetime.today())).date()
        except:
            f_venc_orig = datetime.today().date()
            
        with st.expander("📝 Abrir Editor Manual de la Transacción Seleccionada"):
            ec1, ec2 = st.columns(2)
            with ec1:
                edit_fecha = st.date_input("Editar Fecha", fecha_orig, key=f"ed_f_{id_seleccionado}").strftime('%Y-%m-%d')
                lista_tipos = ["Ingreso", "Egreso"]
                edit_tipo = st.selectbox("Editar Tipo", lista_tipos, index=lista_tipos.index(fila_sel['tipo']) if fila_sel['tipo'] in lista_tipos else 0, key=f"ed_t_{id_seleccionado}")
                edit_cat = st.text_input("Editar Categoría", str(fila_sel.get('categoria', 'GENERAL')), key=f"ed_c_{id_seleccionado}").strip().upper()
                edit_concepto = st.text_input("Editar Concepto/Descripción", str(fila_sel.get('concepto', '')), key=f"ed_con_{id_seleccionado}").strip()
            with ec2:
                edit_monto = st.number_input("Editar Monto ($)", min_value=0.0, value=float(fila_sel['monto']), step=100.0, key=f"ed_m_{id_seleccionado}")
                lista_pagos = ["Efectivo", "Transferencia", "Cheque", "Crédito"]
                edit_pago = st.selectbox("Editar Método Pago", lista_pagos, index=lista_pagos.index(fila_sel.get('metodo_pago', 'Efectivo')) if fila_sel.get('metodo_pago', 'Efectivo') in lista_pagos else 0, key=f"ed_p_{id_seleccionado}")
                
                opciones_lotes_ed = ["Ninguno"]
                if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                    opciones_lotes_ed += list(df_lotes['nombre_lote'].dropna().unique())
                lote_actual = fila_sel.get('lote_asociado', 'Ninguno')
                idx_lote = opciones_lotes_ed.index(lote_actual) if lote_actual in opciones_lotes_ed else 0
                edit_lote = st.selectbox("Editar Lote Asociado", opciones_lotes_ed, index=idx_lote, key=f"ed_l_{id_seleccionado}")
                
                lista_estados = ["Pagado", "Pendiente"]
                edit_estado = st.selectbox("Editar Estado Pago", lista_estados, index=lista_estados.index(fila_sel['estado_deuda']) if fila_sel['estado_deuda'] in lista_estados else 0, key=f"ed_est_{id_seleccionado}")
                edit_venc = st.date_input("Editar Vencimiento", f_venc_orig, key=f"ed_v_{id_seleccionado}").strftime('%Y-%m-%d')

            btn_act, btn_elim = st.columns(2)
            with btn_act:
                if st.button("🔄 Guardar Cambios Manuales", key=f"btn_up_fin_{id_seleccionado}", use_container_width=True):
                    if edit_monto <= 0:
                        st.error("El monto debe ser superior a $0")
                    elif not edit_concepto:
                        st.error("El concepto no puede estar vacío")
                    else:
                        registro_actualizado = {
                            "id": str(id_seleccionado), "fecha": edit_fecha, "tipo": edit_tipo,
                            "categoria": edit_cat, "concepto": edit_concepto, "monto": float(edit_monto),
                            "metodo_pago": edit_pago, "lote_asociado": edit_lote, "estado_deuda": edit_estado,
                            "fecha_vencimiento": edit_venc
                        }
                        if guardar_registro("finanzas", registro_actualizado, "id"):
                            st.success("¡Transacción actualizada!")
                            time.sleep(0.4)
                            st.rerun()
            with btn_elim:
                if st.button("🗑️ Eliminar permanentemente", key=f"btn_del_fin_{id_seleccionado}", use_container_width=True, type="primary"):
                    if eliminar_registro("finanzas", "id", id_seleccionado):
                        st.warning("Registro eliminado.")
                        time.sleep(0.4)
                        st.rerun()

# PESTAÑA EMPLEADOS
with tabs[1]:
    st.subheader("Administración de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        e_nombre = st.text_input("Nombre del Empleado").strip().upper()
        e_tel = st.text_input("Teléfono (10 dígitos)").strip()
        e_puesto = st.text_input("Puesto").strip().upper()
        submit_empleado = st.form_submit_button("💾 Guardar Empleado")
        
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
        if st.button("🗑️ Eliminar Empleado"):
            if eliminar_registro("empleados", "nombre", emp_sel):
                time.sleep(0.4)
                st.rerun()

# PESTAÑA CLIENTES
with tabs[2]:
    st.subheader("Registro de Clientes")
    with st.form("form_clientes", clear_on_submit=True):
        c_nombre = st.text_input("Razón Social / Nombre").strip().upper()
        c_tel = st.text_input("Teléfono (10 dígitos)").strip()
        submit_cliente = st.form_submit_button("💾 Guardar Cliente")
        
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

# PESTAÑA PROVEEDORES
with tabs[3]:
    st.subheader("Catálogo de Proveedores")
    with st.form("form_proveedores", clear_on_submit=True):
        p_nombre = st.text_input("Nombre del Proveedor / Razón Social").strip().upper()
        p_insumo = st.text_input("Insumo Principal (Ej: Alimento, Medicinas, Diésel)").strip().upper()
        p_contacto = st.text_input("Información de Contacto (Teléfono / Correo)").strip()
        submit_prov = st.form_submit_button("💾 Guardar Proveedor")
        
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
        if st.button("🗑️ Eliminar Proveedor"):
            if eliminar_registro("proveedores", "nombre_proveedor", prov_sel):
                time.sleep(0.4)
                st.rerun()

# PESTAÑA LOTES
with tabs[4]:
    st.subheader("Control de Lotes de Ganado")
    with st.form("form_lotes", clear_on_submit=True):
        l_nombre = st.text_input("Código del Lote (Ej: LOTE_SARDO_01)").strip().upper()
        col_lote_1, col_lote_2 = st.columns(2)
        with col_lote_1:
            l_cabezas = st.number_input("Número de cabezas de ganado:", min_value=0, step=1, value=10)
        with col_lote_2:
            l_raza = st.text_input("Raza / Genética preponderante (Ej: SARDO NEGRO, SUIZBU):").strip().upper()
            
        l_desc = st.text_area("Notas Adicionales de Alimentación o Potrero").strip()
        submit_lote = st.form_submit_button("💾 Guardar Lote")
        
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
                label="📥 Descargar Respaldo Excel", 
                data=buffer.getvalue(),
                file_name=f"Respaldo_Rancho_AE_{datetime.now().strftime('%Y-%m-%d')}.xlsx", 
                mime="application/vnd.ms-excel", 
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error al generar el respaldo: {e}")
