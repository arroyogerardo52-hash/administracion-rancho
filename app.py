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
        st.subheader("📋 Transacciones del Período")
        
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

        st.write("### 📄 Exportar Reporte Ejecutivo")
        
        f_ini_str = fecha_inicio.strftime('%d/%m/%Y') if fecha_inicio else 'Inicio'
        f_fin_str = fecha_fin.strftime('%d/%m/%Y') if fecha_fin else 'Fin'
        
        html_reporte = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; color: #333333; line-height: 1.6; }}
                h1 {{ color: #1f4e79; border-bottom: 2px solid #1f4e79; padding-bottom: 5px; }}
                h2 {{ color: #2e75b6; margin-top: 20px; }}
                .metric-box {{ padding: 10px; margin: 5px; border: 1px solid #ddd; background-color: #f9f9f9; display: inline-block; width: 18%; text-align: center; }}
                .positive {{ color: green; font-weight: bold; }}
                .negative {{ color: red; font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
                th {{ background-color: #1f4e79; color: white; padding: 8px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Reporte de Balance y Control Financiero</h1>
            <p><strong>Período seleccionado:</strong> {periodo} ({f_ini_str} - {f_fin_str})</p>
            <p><strong>Filtro de Lote:</strong> {lote_seleccionado}</p>
            <p><strong>Fecha de generación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            
            <h2>Resumen Financiero</h2>
            <div class="metric-box"><strong>Ingresos Reales</strong><br><span class="positive">${ingresos:,.2f}</span></div>
            <div class="metric-box"><strong>Egresos Reales</strong><br><span class="negative">${egresos:,.2f}</span></div>
            <div class="metric-box"><strong>Balance Neto</strong><br><span class="{'positive' if balance_neto >= 0 else 'negative'}">${balance_neto:,.2f}</span></div>
            <div class="metric-box"><strong>Por Cobrar</strong><br><span style="color:#2e75b6;">${por_cobrar:,.2f}</span></div>
            <div class="metric-box"><strong>Por Pagar</strong><br><span style="color:#e46c0a;">${por_pagar:,.2f}</span></div>
            
            <h2>Desglose de Movimientos Registrados</h2>
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Concepto/Detalle</th>
                        <th>Tipo</th>
                        <th>Monto</th>
                        <th>Lote</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, fila in df_filtrado.iterrows():
            f_date = fila['fecha'].strftime('%d/%m/%Y') if pd.notnull(fila['fecha']) else ''
            concepto = fila.get('concepto', fila.get('detalle', 'Sin concepto'))
            lote_asoc = fila.get('lote_asociado', 'Ninguno')
            html_reporte += f"""
                    <tr>
                        <td>{f_date}</td>
                        <td>{concepto}</td>
                        <td>{fila['tipo']}</td>
                        <td>${fila['monto']:,.2f}</td>
                        <td>{lote_asoc}</td>
                        <td>{fila['estado_deuda']}</td>
                    </tr>
            """
            
        html_reporte += """
                </tbody>
            </table>
            <p style='margin-top:30px; font-size:11px; color:#777;'>Generado automáticamente por el Panel de Administración Financiera.</p>
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

    # MÓDULO ACTUALIZADO: Edición Completa Manual de Transacciones
    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        
        id_seleccionado = st.selectbox("Selecciona ID a alterar:", df_finanzas['id'].unique(), key="del_fin")
        fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
        
        # Parseo seguro de fechas originales
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
                            st.session_state["mostrar_descarga"] = False
                            time.sleep(0.4)
                            st.rerun()
            with btn_elim:
                if st.button("🗑️ Eliminar permanentemente", key=f"btn_del_fin_{id_seleccionado}", use_container_width=True, type="primary"):
                    if eliminar_registro("finanzas", "id", id_seleccionado):
                        st.warning("Registro eliminado.")
                        st.session_state["mostrar_descarga"] = False
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
                
    buscar_cli = st.text_input("🔍 Buscar Cliente:", key="bus_cli").strip()
    df_cli_vista = df_clientes.copy()
    
    if buscar_cli and not df_cli_vista.empty:
        df_cli_vista = df_cli_vista[df_cli_vista.astype(str).apply(lambda x: x.str.contains(buscar_cli, case=False)).any(axis=1)]
        
    st.dataframe(df_cli_vista, use_container_width=True, hide_index=True)
    
    # NUEVO MÓDULO: Edición Manual de Clientes
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
                    
    buscar_prov = st.text_input("🔍 Buscar Proveedor:", key="bus_prov").strip()
    df_prov_vista = df_proveedores.copy()
    
    columnas_prov = ["nombre_proveedor", "insumo_principal"]
    if "contacto" in df_prov_vista.columns:
        columnas_prov.append("contacto")
    df_prov_vista = df_prov_vista.reindex(columns=columnas_prov)
    
    if buscar_prov and not df_prov_vista.empty:
        df_prov_vista = df_prov_vista[df_prov_vista.astype(str).apply(lambda x: x.str.contains(buscar_prov, case=False)).any(axis=1)]
        
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
                    "descripcion_notes": l_desc, 
                    "fecha_creacion": datetime.today().strftime('%Y-%m-%d')
                }
                if guardar_registro("lotes", registro_lote, "nombre_lote"):
                    st.success(f"¡Lote {l_nombre} guardado con éxito con datos estructurados!")
                    time.sleep(0.4)
                    st.rerun()
                
    buscar_lote = st.text_input("🔍 Buscar Lote:", key="bus_lote").strip()
    df_lotes_vista = df_lotes.copy()
    
    if buscar_lote and not df_lotes_vista.empty:
        df_lotes_vista = df_lotes_vista[df_lotes_vista.astype(str).apply(lambda x: x.str.contains(buscar_lote, case=False)).any(axis=1)]
        
    st.dataframe(df_lotes_vista, use_container_width=True, hide_index=True)
    
    # NUEVO MÓDULO: Edición Manual de Lotes (Cabezas, Raza, Notas)
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
