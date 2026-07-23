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
# BARRA LATERAL: LOGO, NAVEGACIÓN Y RESPALDOS
# ==========================================
with st.sidebar:
    st.header("🏢 Imagen Corporativa")
    
    logo_file = st.file_uploader(
        "Sube el Logotipo (PNG/JPG):",
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
            st.image(bytes_data, width=140, caption="Logotipo cargado")
        except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")
    else:
        logo_html_src = "https://images.unsplash.com/photo-1516467508483-a7212febe31a?q=80&w=200&auto=format&fit=crop"
        st.info("💡 Usando logo predeterminado temporalmente.")
    
    st.markdown("---")
    
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
col_title, col_logo = st.columns([4, 1])
with col_title:
    st.title("Rancho AE: Sistema de Administración")
with col_logo:
    if logo_file is not None:
        st.image(logo_file, width=90)

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
        f_str = f_date.strftime('%Y-%m-%d') if hasattr(f_date, 'strftime') else str(f_date)[:10]
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
            Este balance ejecutivo constituye un extracto oficial de la contabilidad interna de Rancho AE.
        </p>
    </body>
    </html>
    """
    return html

# ==========================================
# RENDERIZADO CONDICIONAL DE MÓDULOS
# ==========================================

# MÓDULO 1: DASHBOARD Y FINANZAS
if modulo_activo == "📊 Dashboard & Finanzas":
    st.header("📊 Balance y Control General Financiero")

    # Pestañas principales organizadas
    tab_resumen, tab_graficas, tab_gestion = st.tabs([
        "📋 Resumen Numérico", 
        "📈 Análisis Gráfico", 
        "🛠️ Administrar Transacciones (Editar/Eliminar)"
    ])

    if not df_finanzas.empty:
        # Preprocesamiento de datos
        df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
        df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
        df_finanzas_clean = df_finanzas.dropna(subset=['fecha']).copy()
        
        # Filtros globales
        st.subheader("📆 Filtros de Consulta")
        col_filtro, col_lote_filtro, col_fechas = st.columns([2, 2, 3])
        
        hoy = datetime.today()
        fecha_inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)

        with col_filtro:
            periodo = st.selectbox(
                "Selecciona el período visualizado:",
                ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"],
                key="sel_periodo"
            )

        with col_lote_filtro:
            opciones_filtro_lote = ["Todos los Lotes"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_filtro_lote += list(df_lotes['nombre_lote'].dropna().unique())
            lote_seleccionado = st.selectbox("Filtrar por Lote Asociado:", opciones_filtro_lote, key="sel_lote_filtro")

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
                rango_fechas = st.date_input("Selecciona el rango (Inicio - Fin):", [fecha_defecto_inicio, fecha_defecto_fin], key="input_rango")
                if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[1], datetime.max.time())
                    st.info(f"Rango activo: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
                else:
                    st.warning("⏳ Selecciona la fecha de fin.")
                    fecha_inicio, fecha_fin = None, None
            else:
                st.info("Mostrando la totalidad de los datos registrados.")

        df_filtrado = df_finanzas_clean.copy()
        
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

        # TAB 1: RESUMEN NUMÉRICO
        with tab_resumen:
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("🟢 Ingresos Reales", f"${ingresos:,.2f}")
            m2.metric("🔴 Egresos Reales", f"${egresos:,.2f}")
            m3.metric("💰 Balance Neto", f"${balance_neto:,.2f}", delta=f"${balance_neto:,.2f}", delta_color="normal" if balance_neto >= 0 else "inverse")
            m4.metric("📈 Por Cobrar", f"${por_cobrar:,.2f}")
            m5.metric("📉 Por Pagar", f"${por_pagar:,.2f}")
            
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
                        file_name=f"Reporte_Ejecutivo_Finanzas_{datetime.now().strftime('%Y%m%d')}.doc",
                        mime="application/msword",
                        use_container_width=True
                    )
            
            buscar_bal = st.text_input("🔍 Buscar en las transacciones:", key="bus_bal").strip()
            df_bal_vista = df_filtrado.copy()
            
            if buscar_bal:
                mascara = df_bal_vista.astype(str).apply(lambda x: x.str.contains(buscar_bal, case=False)).any(axis=1)
                df_bal_vista = df_bal_vista[mascara]
                
            if not df_bal_vista.empty:
                df_bal_vista['fecha'] = df_bal_vista['fecha'].dt.strftime('%Y-%m-%d')
                df_bal_estilizado = (df_bal_vista.style.apply(colorear_filas_finanzas, axis=1).format({'monto': '${:,.2f}'}))
                st.dataframe(df_bal_estilizado, use_container_width=True)
            else:
                st.info("No hay registros que coincidan con la búsqueda.")

        # TAB 2: GRÁFICAS
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
                        st.info("No hay transacciones pagadas para graficar.")
                
                with cg2:
                    st.write("### 📌 Flujo por Categoría")
                    col_cat = 'categoria' if 'categoria' in df_filtrado.columns else 'tipo'
                    df_cat = df_filtrado.groupby([col_cat, 'tipo'])['monto'].sum().unstack().fillna(0.0)
                    st.bar_chart(df_cat, use_container_width=True)
            else:
                st.info("Sin registros en el rango seleccionado.")

        # TAB 3: GESTIÓN (EDITAR Y ELIMINAR REGISTROS)
        with tab_gestion:
            st.subheader("🛠️ Modificar o Eliminar Transacciones Existentes")
            lista_ids = df_finanzas['id'].astype(str).unique()
            
            id_seleccionado = st.selectbox("Selecciona la transacción por ID:", lista_ids, key="sel_id_modificar")
            
            if id_seleccionado:
                fila_sel = df_finanzas[df_finanzas['id'].astype(str) == id_seleccionado].iloc[0]
                
                try:
                    fecha_orig = pd.to_datetime(fila_sel['fecha']).date()
                except:
                    fecha_orig = datetime.today().date()
                    
                try:
                    f_venc_orig = pd.to_datetime(fila_sel.get('fecha_vencimiento', datetime.today())).date()
                except:
                    f_venc_orig = datetime.today().date()

                st.info(f"Modificando registro ID: **{id_seleccionado}** - {fila_sel.get('concepto', '')}")
                
                ec1, ec2 = st.columns(2)
                with ec1:
                    edit_fecha = st.date_input("Fecha", fecha_orig, key=f"ed_f_{id_seleccionado}").strftime('%Y-%m-%d')
                    lista_tipos = ["Ingreso", "Egreso"]
                    edit_tipo = st.selectbox("Tipo", lista_tipos, index=lista_tipos.index(fila_sel['tipo']) if fila_sel['tipo'] in lista_tipos else 0, key=f"ed_t_{id_seleccionado}")
                    edit_cat = st.text_input("Categoría", str(fila_sel.get('categoria', 'GENERAL')), key=f"ed_c_{id_seleccionado}").strip().upper()
                    edit_concepto = st.text_input("Concepto / Descripción", str(fila_sel.get('concepto', '')), key=f"ed_con_{id_seleccionado}").strip()
                with ec2:
                    edit_monto = st.number_input("Monto ($)", min_value=0.0, value=float(fila_sel['monto']), step=100.0, key=f"ed_m_{id_seleccionado}")
                    lista_pagos = ["Efectivo", "Transferencia", "Cheque", "Crédito"]
                    edit_pago = st.selectbox("Método Pago", lista_pagos, index=lista_pagos.index(fila_sel.get('metodo_pago', 'Efectivo')) if fila_sel.get('metodo_pago', 'Efectivo') in lista_pagos else 0, key=f"ed_p_{id_seleccionado}")
                    
                    opciones_lotes_ed = ["Ninguno"]
                    if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                        opciones_lotes_ed += list(df_lotes['nombre_lote'].dropna().unique())
                    lote_actual = fila_sel.get('lote_asociado', 'Ninguno')
                    idx_lote = opciones_lotes_ed.index(lote_actual) if lote_actual in opciones_lotes_ed else 0
                    edit_lote = st.selectbox("Lote Asociado", opciones_lotes_ed, index=idx_lote, key=f"ed_l_{id_seleccionado}")
                    
                    lista_estados = ["Pagado", "Pendiente"]
                    edit_estado = st.selectbox("Estado Pago", lista_estados, index=lista_estados.index(fila_sel['estado_deuda']) if fila_sel['estado_deuda'] in lista_estados else 0, key=f"ed_est_{id_seleccionado}")
                    edit_venc = st.date_input("Fecha Vencimiento", f_venc_orig, key=f"ed_v_{id_seleccionado}").strftime('%Y-%m-%d')

                st.write("---")
                btn_act, btn_elim = st.columns(2)
                
                with btn_act:
                    if st.button("🔄 Guardar Cambios", key=f"btn_up_fin_{id_seleccionado}", use_container_width=True):
                        if edit_monto <= 0:
                            st.error("❌ El monto debe ser mayor a $0")
                        elif not edit_concepto:
                            st.error("❌ El concepto no puede estar vacío")
                        else:
                            registro_actualizado = {
                                "id": str(id_seleccionado), "fecha": edit_fecha, "tipo": edit_tipo,
                                "categoria": edit_cat, "concepto": edit_concepto, "monto": float(edit_monto),
                                "metodo_pago": edit_pago, "lote_asociado": edit_lote, "estado_deuda": edit_estado,
                                "fecha_vencimiento": edit_venc
                            }
                            if guardar_registro("finanzas", registro_actualizado, "id"):
                                st.success("✅ Transacción actualizada correctamente.")
                                time.sleep(0.5)
                                st.rerun()

                with btn_elim:
                    if st.button("🗑️ Eliminar Registro", key=f"btn_del_fin_{id_seleccionado}", use_container_width=True, type="primary"):
                        if eliminar_registro("finanzas", "id", id_seleccionado):
                            st.success("✅ Transacción eliminada permanentemente.")
                            time.sleep(0.5)
                            st.rerun()
    else:
        st.warning("No se encontraron registros financieros para procesar en la base de datos.")

    st.markdown("---")
    
    # REGISTRO DE NUEVAS TRANSACCIONES
    st.subheader("➕ Agregar Nueva Transacción")
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
            
        submit_finanzas = st.form_submit_button("💾 Guardar Transacción", use_container_width=True)
        if submit_finanzas:
            if f_monto <= 0:
                st.error("❌ El monto debe ser mayor a $0.00 pesos.")
            elif not f_concepto:
                st.error("❌ Por favor escribe un Concepto o Descripción.")
            else:
                auto_id = f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}"
                nuevo_registro = {
                    "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat if f_cat else "GENERAL",
                    "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                    "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
                }
                if guardar_registro("finanzas", nuevo_registro, "id"):
                    st.success(f"¡Transacción registrada con ID: {auto_id}!")
                    time.sleep(0.5)
                    st.rerun()

# MÓDULOS RESTANTES
elif modulo_activo == "🤠 Personal / Empleados":
    st.header("🤠 Gestión de Personal y Empleados")
    st.dataframe(df_empleados, use_container_width=True)

elif modulo_activo == "🤝 Clientes":
    st.header("🤝 Directorio de Clientes")
    st.dataframe(df_clientes, use_container_width=True)

elif modulo_activo == "🚜 Proveedores":
    st.header("🚜 Directorio de Proveedores")
    st.dataframe(df_proveedores, use_container_width=True)

elif modulo_activo == "🐂 Control de Lotes":
    st.header("🐂 Administración de Lotes y Ganado")
    st.dataframe(df_lotes, use_container_width=True)
