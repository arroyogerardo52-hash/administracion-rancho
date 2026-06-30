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

# Carga de datos
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

st.markdown("---")

# ==========================================
# 5. PESTAÑAS OPERATIVAS (TODAS LAS FUNCIONES)
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# PESTAÑA 1: FINANZAS
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
            
        if st.form_submit_button("Guardar Transacción"):
            auto_id = f"TRA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            nuevo_registro = {
                "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_fecha
            }
            if guardar_registro("finanzas", nuevo_registro, "id"):
                st.success("¡Transacción registrada exitosamente!")
                st.rerun()

    st.write("### Historial de Movimientos")
    st.dataframe(df_finanzas, use_container_width=True, hide_index=True)

    if not df_finanzas.empty:
        st.write("#### 🗑️ Eliminar Registro Financiero")
        id_eliminar = st.selectbox("Selecciona ID a eliminar:", df_finanzas['id'].unique())
        if st.button("Confirmar Eliminación Transacción"):
            if eliminar_registro("finanzas", "id", id_eliminar):
                st.success("Registro eliminado.")
                st.rerun()

# PESTAÑA 2: EMPLEADOS
with tabs[1]:
    st.subheader("🤠 Control de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        e_nombre = st.text_input("Nombre Completo")
        e_tel = st.text_input("Teléfono")
        e_puesto = st.text_input("Puesto / Función")
        if st.form_submit_button("Guardar Empleado"):
            if e_nombre.strip():
                datos_emp = {"nombre": e_nombre.strip(), "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": datetime.today().strftime('%Y-%m-%d')}
                if guardar_registro("empleados", datos_emp, "nombre"):
                    st.success("Empleado guardado.")
                    st.rerun()
    st.dataframe(df_empleados, use_container_width=True, hide_index=True)
    if not df_empleados.empty:
        emp_sel = st.selectbox("Selecciona para eliminar:", df_empleados['nombre'].unique(), key="del_emp")
        if st.button("Eliminar Empleado"):
            if eliminar_registro("empleados", "nombre", emp_sel): st.rerun()

# PESTAÑA 3: CLIENTES
with tabs[2]:
    st.subheader("🤝 Registro de Clientes")
    with st.form("form_clientes", clear_on_submit=True):
        c_nombre = st.text_input("Nombre / Razón Social")
        c_tel = st.text_input("Teléfono")
        if st.form_submit_button("Guardar Cliente"):
            if c_nombre.strip():
                datos_cli = {"nombre_razon": c_nombre.strip(), "telefono": c_tel}
                if guardar_registro("clientes", datos_cli, "nombre_razon"):
                    st.success("Cliente guardado.")
                    st.rerun()
    st.dataframe(df_clientes, use_container_width=True, hide_index=True)
    if not df_clientes.empty:
        cli_sel = st.selectbox("Selecciona para eliminar:", df_clientes['nombre_razon'].unique(), key="del_cli")
        if st.button("Eliminar Cliente"):
            if eliminar_registro("clientes", "nombre_razon", cli_sel): st.rerun()

# PESTAÑA 4: PROVEEDORES
with tabs[3]:
    st.subheader("🚜 Catálogo de Proveedores")
    with st.form("form_proveedores", clear_on_submit=True):
        p_nombre = st.text_input("Nombre de la Empresa")
        p_insumo = st.text_input("Insumo Principal")
        if st.form_submit_button("Guardar Proveedor"):
            if p_nombre.strip():
                datos_prov = {"nombre_proveedor": p_nombre.strip(), "insumo_principal": p_insumo}
                if guardar_registro("proveedores", datos_prov, "nombre_proveedor"):
                    st.success("Proveedor guardado.")
                    st.rerun()
    st.dataframe(df_proveedores, use_container_width=True, hide_index=True)
    if not df_proveedores.empty:
        prov_sel = st.selectbox("Selecciona para eliminar:", df_proveedores['nombre_proveedor'].unique(), key="del_prov")
        if st.button("Eliminar Proveedor"):
            if eliminar_registro("proveedores", "nombre_proveedor", prov_sel): st.rerun()

# PESTAÑA 5: LOTES
with tabs[4]:
    st.subheader("🐂 Control de Lotes de Ganado")
    with st.form("form_lotes", clear_on_submit=True):
        l_nombre = st.text_input("Código o Nombre del Lote")
        l_desc = st.text_area("Notas / Especificaciones")
        if st.form_submit_button("Guardar Lote"):
            if l_nombre.strip():
                datos_lote = {"nombre_lote": l_nombre.strip(), "descripcion_notas": l_desc, "fecha_creacion": datetime.today().strftime('%Y-%m-%d')}
                if guardar_registro("lotes", datos_lote, "nombre_lote"):
                    st.success("Lote guardado.")
                    st.rerun()
    st.dataframe(df_lotes, use_container_width=True, hide_index=True)
    if not df_lotes.empty:
        lote_sel = st.selectbox("Selecciona para eliminar:", df_lotes['nombre_lote'].unique(), key="del_lote")
        if st.button("Eliminar Lote"):
            if eliminar_registro("lotes", "nombre_lote", lote_sel): st.rerun()
