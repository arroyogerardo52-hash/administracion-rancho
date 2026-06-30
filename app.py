import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64

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
    st.title("🤠 Rancho AE: Sistema de Administración")
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

# --- NUEVA SECCIÓN DE FILTROS TEMPORALES ---
col_f1, col_f2 = st.columns([2, 3])
with col_f1:
    periodo = st.selectbox(
        "📆 Rango del Balance:",
        ["Todo el Historial", "Semana Actual", "Mes Actual", "Año Actual", "Búsqueda Personalizada"]
    )

df_filtrado = df_finanzas.copy()
hoy = datetime.today().date()
fecha_inicio, fecha_fin = None, None

if periodo == "Semana Actual":
    fecha_inicio = hoy - timedelta(days=hoy.weekday())
    fecha_fin = fecha_inicio + timedelta(days=6)
elif periodo == "Mes Actual":
    fecha_inicio = hoy.replace(day=1)
    next_month = hoy.replace(day=28) + timedelta(days=4)
    fecha_fin = next_month - timedelta(days=next_month.day)
elif periodo == "Año Actual":
    fecha_inicio = hoy.replace(month=1, day=1)
    fecha_fin = hoy.replace(month=12, day=31)
elif periodo == "Búsqueda Personalizada":
    with col_f2:
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            fecha_inicio = st.date_input("Desde:", hoy - timedelta(days=30))
        with c_f2:
            fecha_fin = st.date_input("Hasta:", hoy)

# Aplicar filtros de fecha si corresponde
if not df_filtrado.empty and 'fecha' in df_filtrado.columns:
    df_filtrado['fecha'] = pd.to_datetime(df_filtrado['fecha']).dt.date
    if fecha_inicio and fecha_fin:
        if isinstance(fecha_inicio, datetime): fecha_inicio = fecha_inicio.date()
        if isinstance(fecha_fin, datetime): fecha_fin = fecha_fin.date()
        df_filtrado = df_filtrado[(df_filtrado['fecha'] >= fecha_inicio) & (df_filtrado['fecha'] <= fecha_fin)]

ingresos, egresos, balance_neto, por_cobrar, por_pagar = 0.0, 0.0, 0.0, 0.0, 0.0

if not df_filtrado.empty:
    df_filtrado['monto'] = pd.to_numeric(df_filtrado['monto'], errors='coerce').fillna(0.0)
    
    ingresos = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    
    por_cobrar = df_filtrado[(df_filtrado['tipo'] == 'Ingreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_filtrado[(df_filtrado['tipo'] == 'Egreso') & (df_filtrado['estado_deuda'] == 'Pendiente')]['monto'].sum()
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🟢 Ingresos Reales", f"${ingresos:,.2f}")
    m2.metric("🔴 Egresos Reales", f"${egresos:,.2f}")
    m3.metric("💰 Balance Neto Actual", f"${balance_neto:,.2f}", delta=f"${balance_neto:,.2f}" if balance_neto >= 0 else f"${balance_neto:,.2f}", delta_color="normal" if balance_neto >= 0 else "inverse")
    m4.metric("📈 Por Cobrar (Clientes)", f"${por_cobrar:,.2f}")
    m5.metric("📉 Por Pagar (Proveedores)", f"${por_pagar:,.2f}")

    # --- NUEVA SECCIÓN DE GRÁFICOS ---
    with st.expander("📈 Visualizar Gráficos de Rendimiento Financiero", expanded=False):
        g1, g2 = st.columns(2)
        with g1:
            st.write("#### Distribución de Flujo Efectivo")
            datos_barras = pd.DataFrame({
                "Monto ($)": [ingresos, egresos, por_cobrar, por_pagar],
                "Concepto": ["Ingresos (Pagado)", "Egresos (Pagado)", "Por Cobrar", "Por Pagar"]
            })
            st.bar_chart(data=datos_barras, x="Concepto", y="Monto ($)", use_container_width=True)
        
        with g2:
            st.write("#### Gastos/Ingresos por Categoría")
            if 'categoria' in df_filtrado.columns and not df_filtrado.empty:
                df_cat = df_filtrado.groupby(['categoria', 'tipo'])['monto'].sum().unstack().fillna(0)
                st.dataframe(df_cat, use_container_width=True)
            else:
                st.info("Sin categorías suficientes en este periodo.")
    
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
                    <tr><td style="padding: 8px;">📈 Cuentas Pendientes de Cobro</td><td style="padding: 8px;">{por_cobrar:,.2f}</td></tr>
                    <tr><td style="padding: 8px;">📉 Cuentas Pendientes de Pago</td><td style="padding: 8px;">{por_pagar:,.2f}</td></tr>
                </tbody>
            </table>
            
            <br>
            <h2 style="color: #5c4033; border-left: 4px solid #5c4033; padding-left: 8px; font-size: 14pt; margin-top: 20px;">2. Libro Diario Reciente Filtrado</h2>
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
            for _, r in df_filtrado.head(30).iterrows():
                html_template += f"""
                <tr>
                    <td style="padding: 6px;">{r.get('id','')}</td>
                    <td style="padding: 6px;">{r.get('fecha','')}</td>
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
            <table style="width: 100%; margin-top: 40px; text-align: center; font-size: 11
