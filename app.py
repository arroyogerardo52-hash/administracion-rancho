import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

st.title("🤠 Rancho AE: Sistema de Administración")
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
        st.error(f"Error al leer la tabla {nombre_tabla}: {e}")
        return pd.DataFrame()

def guardar_registro(nombre_tabla, datos, llave_primaria):
    try:
        supabase.table(nombre_tabla).upsert(datos, on_conflict=llave_primaria).execute()
        return True
    except Exception as e:
        st.error(f"Error al guardar en la tabla {nombre_tabla}: {e}")
        return False

def eliminar_registro(nombre_tabla, columna_llave, valor_llave):
    try:
        supabase.table(nombre_tabla).delete().eq(columna_llave, valor_llave).execute()
        return True
    except Exception as e:
        st.error(f"Error al eliminar en la tabla {nombre_tabla}: {e}")
        return False

# Carga de datos global
df_finanzas = cargar_tabla("finanzas")
df_empleados = cargar_tabla("empleados")
df_clientes = cargar_tabla("clientes")
df_proveedores = cargar_tabla("proveedores")
df_lotes = cargar_tabla("lotes")

# ==========================================
# 4. FILTROS TEMPORALES Y BALANCE
# ==========================================
st.header("📊 Balance y Análisis Financiero")

periodo = st.selectbox(
    "📆 Selecciona el Periodo de Análisis:",
    ["Todo el Historial", "Semana Actual", "Mes Actual", "Año Actual"]
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

if not df_filtrado.empty and 'fecha' in df_filtrado.columns:
    df_filtrado['fecha'] = pd.to_datetime(df_filtrado['fecha']).dt.date
    if fecha_inicio and fecha_fin:
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
m3.metric("💰 Balance Neto", f"${balance_neto:,.2f}")
m4.metric("📈 Por Cobrar", f"${por_cobrar:,.2f}")
m5.metric("📉 Por Pagar", f"${por_pagar:,.2f}")

if not df_filtrado.empty:
    datos_barras = pd.DataFrame({
        "Monto ($)": [ingresos, egresos, por_cobrar, por_pagar],
        "Concepto Financiero": ["Ingresos (Pagado)", "Egresos (Pagado)", "Por Cobrar", "Por Pagar"]
    })
    st.bar_chart(data=datos_barras, x="Concepto Financiero", y="Monto ($)", use_container_width=True)
else:
    st.info("No hay datos liquidados en este periodo para graficar por categorías.")

st.markdown("---")

# ==========================================
# 5. PESTAÑAS OPERATIVAS PRINCIPALES
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# --- PESTAÑA 1: FINANZAS ---
with tabs[0]:
    st.subheader("📝 Registro de Transacciones")
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_fecha = st.date_input("Fecha Transacción", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
            f_cat = st.text_input("Categoría (Ej: Alimento, Vacunas, Venta Ganado)")
            f_concepto = st.text_input("Concepto / Descripción")
        with col2:
            f_monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
            f_pago = st.selectbox("Método de Pago", ["Transferencia", "Efectivo", "Crédito"])
            
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            
        if st.form_submit_button("💾 Guardar Transacción en Servidor"):
            auto_id = f"TRA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            nuevo_registro = {
                "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_fecha
            }
            if guardar_registro("finanzas", nuevo_registro, "id"):
                st.success("¡Transacción registrada exitosamente!")
                st.rerun()

    st.write("### Historial General de Movimientos")
    st.dataframe(df_finanzas, use_container_width=True, hide_index=True)

    if not df_finanzas.empty:
        st.write("#### 🗑️ Eliminar Registro Financiero")
        id_eliminar = st.selectbox("Selecciona ID de Transacción a eliminar:", df_finanzas['id'].unique())
        if st.button("Confirmar Eliminación de Transacción"):
            if eliminar_registro("finanzas", "id", id_eliminar):
                st.success("Registro eliminado correctamente.")
                st.rerun()

    # --- SECCIÓN DE EXPORTACIÓN Y REPORTE REINSTALADA ---
    st.markdown("---")
    st.header("📝 Exportar Estado de Cuenta Oficial")
    
    if st.button("📝 Compilar Plantilla Institucional con Logotipo"):
        fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Tabla de Finanzas en HTML estructurado
        tabla_html = ""
        if not df_filtrado.empty:
            tabla_html += """
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%; border: 1px solid #dddddd;">
                <thead>
                    <tr style="background-color: #f8f9fa; text-align: left;">
                        <th>Fecha</th><th>Tipo</th><th>Categoría</th><th>Concepto</th><th>Monto</th><th>Estado</th>
                    </tr>
                </thead>
                <tbody>
            """
            for _, row in df_filtrado.iterrows():
                color_tipo = "green" if row.get('tipo') == "Ingreso" else "red"
                tabla_html += f"""
                    <tr>
                        <td>{row.get('fecha','')}</td>
                        <td style="color: {color_tipo}; font-weight: bold;">{row.get('tipo','')}</td>
                        <td>{row.get('categoria','')}</td>
                        <td>{row.get('concepto','')}</td>
                        <td>${float(row.get('monto',0)):,.2f}</td>
                        <td>{row.get('estado_deuda','')}</td>
                    </tr>
                """
            tabla_html += "</tbody></table>"
        else:
            tabla_html = "<p>No hay transacciones registradas en este periodo.</p>"

        # Reporte HTML Final sin usar componentes experimentales que rompan Streamlit
        html_documento = f"""
        <div style="font-family: Arial, sans-serif; color: #333333; padding: 20px; border: 1px solid #eee;">
            <table style="width: 100%; border-bottom: 2px solid #5c4033; padding-bottom: 10px;">
                <tr>
                    <td>
                        <h1 style="color: #5c4033; margin: 0;">RANCHO AE</h1>
                        <p style="font-style: italic; margin: 5px 0 0 0; color: #666;">Desarrollo Genético y Engorda Comercial</p>
                        <p style="margin: 2px 0; font-size: 12px; color: #888;">Reporte Consolidado de Administración</p>
                    </td>
                    <td style="text-align: right; vertical-align: middle;">
                        <img src="https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?q=80&w=200" width="120" style="border-radius: 8px;" alt="Logo"/>
                    </td>
                </tr>
            </table>
            <br>
            <p><strong>Fecha de Emisión:</strong> {fecha_str}</p>
            <p>Este informe detalla el estado financiero integral extraído de forma segura desde los servidores de administración.</p>
            
            <h2 style="color: #5c4033; border-left: 4px solid #5c4033; padding-left: 8px;">1. Resumen de Saldos Monetarios</h2>
            <ul>
                <li><strong>Ingresos Liquidados:</strong> ${ingresos:,.2f}</li>
                <li><strong>Egresos Liquidados:</strong> ${egresos:,.2f}</li>
                <li><strong>Balance Neto Actual:</strong> ${balance_neto:,.2f}</li>
                <li><strong>Cuentas por Cobrar Pendientes:</strong> ${por_cobrar:,.2f}</li>
                <li><strong>Cuentas por Pagar Pendientes:</strong> ${por_pagar:,.2f}</li>
            </ul>
            
            <h2 style="color: #5c4033; border-left: 4px solid #5c4033; padding-left: 8px;">2. Desglose del Historial</h2>
            {tabla_html}
        </div>
        """
        st.session_state["reporte_html"] = html_documento
        st.success("¡Estructura de la plantilla con logotipo lista para ser exportada!")

    # El expansor ahora muestra el reporte de forma segura como código limpio
    if "reporte_html" in st.session_state:
        with st.expander("👁️ Previsualizar Formato del Documento"):
            st.code(st.session_state["reporte_html"], language="html")
        
        b64 = base64.b64encode(st.session_state["reporte_html"].encode()).decode()
        href = f'<a href="data:text/html;base64,{b64}" download="Estado_Cuenta_Rancho_AE.html" style="text-decoration: none;"><button style="background-color: #5c4033; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">📥 Descargar Estado de Cuenta en HTML</button></a>'
        st.markdown(href, unsafe_allowed_html=True)

# --- PESTAÑA 2: EMPLEADOS ---
with tabs[1]:
    st.subheader("🤠 Control de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        e_nombre = st.text_input("Nombre Completo del Trabajador")
        e_tel = st.text_input("Teléfono de Contacto")
        e_puesto = st.text_input("Puesto / Función en el Rancho")
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre.strip():
                datos_emp = {
                    "nombre": e_nombre.strip(),
                    "telefono": e_tel,
                    "puesto_funcion": e_puesto,
                    "fecha_ingreso": datetime.today().strftime('%Y-%m-%d')
                }
                if guardar_registro("empleados", datos_emp, "nombre"):
                    st.success("Empleado registrado de manera segura.")
                    st.rerun()
            else:
                st.warning("El nombre es un campo obligatorio.")

    st.dataframe(df_empleados, use_container_width=True, hide_index=True)
    if not df_empleados.empty:
        st
