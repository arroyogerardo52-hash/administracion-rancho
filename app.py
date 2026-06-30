import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

st.title("🤠 Rancho AE: Sistema de Administración")
st.markdown("---")

# ==========================================
# 2. VALIDACIÓN DE CREDENCIALES
# ==========================================
credentials_ready = False

if "supabase" in st.secrets:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        if url and key and "supabase.co" in url:
            credentials_ready = True
        else:
            st.error("❌ La URL de Supabase parece tener un formato incorrecto. Debe empezar con 'https://' y terminar con '.supabase.co'")
    except KeyError:
        st.error("❌ Error de formato en Secrets: Asegúrate de usar exactamente las llaves 'url' y 'key'.")
else:
    st.warning("⚠️ Conexión pendiente: Las credenciales de Supabase no están configuradas.")

if not credentials_ready:
    st.stop()

# ==========================================
# 3. CONEXIÓN SEGURA A SUPABASE
# ==========================================
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"No se pudo inicializar el cliente de Supabase: {e}")
        return None

supabase: Client = init_connection()

if supabase is None:
    st.stop()

# Funciones de carga, guardado y eliminación
def cargar_tabla(nombre_tabla):
    try:
        response = supabase.table(nombre_tabla).select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer la tabla {nombre_tabla}: {e}")
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

# Cargar datos globales para los cálculos del Balance
df_finanzas = cargar_tabla("finanzas")
df_empleados = cargar_tabla("empleados")
df_clientes = cargar_tabla("clientes")
df_proveedores = cargar_tabla("proveedores")
df_lotes = cargar_tabla("lotes")

# ==========================================
# 4. PANEL DE BALANCE GLOBAL & ESTADÍSTICAS
# ==========================================
st.header("📊 Balance y Control General Financiero")

if not df_finanzas.empty:
    # Conversión segura de tipos de datos
    df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
    
    # Cálculos métricos básicos
    ingresos = df_finanzas[(df_finanzas['tipo'] == 'Ingreso') & (df_finanzas['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_finanzas[(df_finanzas['tipo'] == 'Egreso') & (df_finanzas['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    
    por_cobrar = df_finanzas[(df_finanzas['tipo'] == 'Ingreso') & (df_finanzas['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_finanzas[(df_finanzas['tipo'] == 'Egreso') & (df_finanzas['estado_deuda'] == 'Pendiente')]['monto'].sum()
    
    # Despliegue de tarjetas de métricas numéricas
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🟢 Ingresos Reales", f"${ingresos:,.2f}")
    m2.metric("🔴 Egresos Reales", f"${egresos:,.2f}")
    
    if balance_neto >= 0:
        m3.metric("💰 Balance Neto Actual", f"${balance_neto:,.2f}", delta=f"${balance_neto:,.2f}")
    else:
        m3.metric("💰 Balance Neto Actual", f"${balance_neto:,.2f}", delta=f"${balance_neto:,.2f}", delta_color="inverse")
        
    m4.metric("📈 Por Cobrar (Clientes)", f"${por_cobrar:,.2f}")
    m5.metric("📉 Por Pagar (Proveedores)", f"${por_pagar:,.2f}")
    
    # Sección para generar el reporte
    st.markdown("### 📝 Exportar Estado de Cuenta Oficial")
    if st.button("📄 Generar Estructura de Reporte para Google Documentos"):
        st.session_state["generar_doc_reporte"] = True
else:
    st.info("💡 Aún no hay registros financieros en la nube para calcular el balance real.")

st.markdown("---")

# ==========================================
# 5. INTERFAZ PRINCIPAL POR PESTAÑAS
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# ------------------------------------------
# PESTAÑA 1: FINANZAS (CON AUTO-ID Y EDICIÓN/ELIMINACIÓN)
# ------------------------------------------
with tabs[0]:
    st.subheader("Registro Financiero Automático")
    
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_fecha = st.date_input("Fecha Transacción", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta Animales, Vacunas)")
            f_concepto = st.text_input("Concepto / Descripción detallada")
        with col2:
            f_monto = st.number_input("Monto total ($)", min_value=0.0, step=100.0)
            f_pago = st.selectbox("Método de Pago Empleado", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote de Ganado Asociado", opciones_lotes)
            
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento (Si aplica)", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Transacción en la Nube"):
            # Generación automática de ID Único
            auto_id = f"TRA-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 100000}"
            nuevo_registro = {
                "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
            }
            if guardar_registro("finanzas", nuevo_registro, "id"):
                st.success(f"¡Transacción registrada automáticamente con ID: {auto_id}!")
                st.rerun()

    st.markdown("### Historial de Movimientos")
    if not df_finanzas.empty:
        columnas_orden = ["id", "fecha", "tipo", "categoria", "concepto", "monto", "metodo_pago", "lote_asociado", "estado_deuda", "fecha_vencimiento"]
        df_finanzas = df_finanzas.reindex(columns=columnas_orden)
    st.dataframe(df_finanzas, use_container_width=True, hide_index=True)

    # Bloque de Edición y Eliminación
    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        id_seleccionado = st.selectbox("Selecciona el ID de la transacción a alterar:", df_finanzas['id'].unique(), key="del_fin")
        fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
        
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            nuevo_estado = st.selectbox("Cambiar Estado Pago a:", ["Pagado", "Pendiente"], index=["Pagado", "Pendiente"].index(fila_sel['estado_deuda']), key="est_fin")
        with c2:
            nuevo_monto = st.number_input("Corregir Monto ($):", min_value=0.0, value=float(fila_sel['monto']), key="mon_fin")
        with c3:
            st.write("")
            st.write("")
            if st.button("🔄 Actualizar", key="btn_up_fin"):
                fila_sel['estado_deuda'] = nuevo_estado
                fila_sel['monto'] = nuevo_monto
                if guardar_registro("finanzas", fila_sel.to_dict(), "id"):
                    st.success("Registro modificado.")
                    st.rerun()
            if st.button("🗑️ Eliminar Registro", key="btn_del_fin"):
                if eliminar_registro("finanzas", "id", id_seleccionado):
                    st.warning("Registro borrado permanentemente.")
                    st.rerun()

# ------------------------------------------
# PESTAÑA 2: EMPLEADOS (CON EDICIÓN/ELIMINACIÓN)
# ------------------------------------------
with tabs[1]:
    st.subheader("Administración de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            e_nombre = st.text_input("Nombre Completo del Empleado")
            e_tel = st.text_input("Teléfono de Contacto")
        with col2:
            e_puesto = st.text_input("Puesto / Función")
            e_ingreso = st.date_input("Fecha de Ingreso", datetime.today()).strftime('%Y-%m-%d')
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre.strip():
                nuevo_registro = {"nombre": e_nombre.strip(), "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": e_ingreso}
                if guardar_registro("empleados", nuevo_registro, "nombre"):
                    st.success("¡Datos guardados!")
                    st.rerun()

    st.markdown("### Plantilla Activa")
    st.dataframe(df_empleados, use_container_width=True, hide_index=True)

    if not df_empleados.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Empleado")
        emp_seleccionado = st.selectbox("Selecciona Empleado:", df_empleados['nombre'].unique())
        if st.button("🗑️ Eliminar Empleado Permanente"):
            if eliminar_registro("empleados", "nombre", emp_seleccionado):
                st.rerun()

# ------------------------------------------
# PESTAÑA 3: CLIENTES (CON EDICIÓN/ELIMINACIÓN)
# ------------------------------------------
with tabs[2]:
    st.subheader("Registro de Clientes")
    with st.form("form_clientes", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            c_nombre = st.text_input("Nombre / Razón Social")
            c_contacto = st.text_input("Persona de Contacto")
        with col2:
            c_tel = st.text_input("Teléfono")
            c_notas = st.text_area("Notas / Condiciones")
        if st.form_submit_button("💾 Guardar Cliente"):
            if c_nombre.strip():
                nuevo_registro = {"nombre_razon": c_nombre.strip(), "contacto": c_contacto, "telefono": c_tel, "notas": c_notas}
                if guardar_registro("clientes", nuevo_registro, "nombre_razon"):
                    st.success("¡Cliente guardado!")
                    st.rerun()

    st.markdown("### Directorio de Clientes")
    st.dataframe(df_clientes, use_container_width=True, hide_index=True)

    if not df_clientes.empty:
        st.markdown("#### 🛠️ Eliminar Cliente")
        cli_seleccionado = st.selectbox("Selecciona Cliente:", df_clientes['nombre_razon'].unique())
        if st.button("🗑️ Eliminar Cliente Permanente"):
            if eliminar_registro("clientes", "nombre_razon", cli_seleccionado):
                st.rerun()

# ------------------------------------------
# PESTAÑA 4: PROVEEDORES (CON EDICIÓN/ELIMINACIÓN)
# ------------------------------------------
with tabs[3]:
    st.subheader("Catálogo de Proveedores")
    with st.form("form_proveedores", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_nombre = st.text_input("Nombre del Proveedor")
            p_contacto = st.text_input("Contacto de Ventas")
        with col2:
            p_tel = st.text_input("Teléfono")
            p_insumo = st.text_input("Insumo Principal")
        if st.form_submit_button("💾 Guardar Proveedor"):
            if p_nombre.strip():
                nuevo_registro = {"nombre_proveedor": p_nombre.strip(), "contacto": p_contacto, "telefono": p_tel, "insumo_principal": p_insumo}
                if guardar_registro("proveedores", nuevo_registro, "nombre_proveedor"):
                    st.success("¡Proveedor guardado!")
                    st.rerun()

    st.markdown("### Lista de Proveedores Autorizados")
    st.dataframe(df_proveedores, use_container_width=True, hide_index=True)

    if not df_proveedores.empty:
        st.markdown("#### 🛠️ Eliminar Proveedor")
        prov_seleccionado = st.selectbox("Selecciona Proveedor:", df_proveedores['nombre_proveedor'].unique())
        if st.button("🗑️ Eliminar Proveedor Permanente"):
            if eliminar_registro("proveedores", "nombre_proveedor", prov_seleccionado):
                st.rerun()

# ------------------------------------------
# PESTAÑA 5: LOTES (CON EDICIÓN/ELIMINACIÓN)
# ------------------------------------------
with tabs[4]:
    st.subheader("Control de Lotes de Ganado")
    with st.form("form_lotes", clear_on_submit=True):
        l_nombre = st.text_input("Nombre o Código del Lote (Ej: Lote_Sardo_01)")
        l_desc = st.text_area("Descripción (Razas, Propósito)")
        l_creacion = st.date_input("Fecha de Creación", datetime.today()).strftime('%Y-%m-%d')
        if st.form_submit_button("💾 Guardar Lote"):
            if l_nombre.strip():
                nuevo_registro = {"nombre_lote": l_nombre.strip(), "descripcion_notas": l_desc, "fecha_creacion": l_creacion}
                if guardar_registro("lotes", nuevo_registro, "nombre_lote"):
                    st.success("¡Lote registrado!")
                    st.rerun()

    st.markdown("### Lotes Activos en el Rancho")
    st.dataframe(df_lotes, use_container_width=True, hide_index=True)

    if not df_lotes.empty:
        st.markdown("#### 🛠️ Eliminar Lote")
        lote_seleccionado = st.selectbox("Selecciona Lote:", df_lotes['nombre_lote'].unique())
        if st.button("🗑️ Eliminar Lote Permanente"):
            if eliminar_registro("lotes", "nombre_lote", lote_seleccionado):
                st.rerun()

# ==========================================
# 6. BARRA LATERAL: RESPALDO EXCEL
# ==========================================
with st.sidebar:
    st.header("⚙️ Copias de Seguridad")
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_finanzas.to_excel(writer, sheet_name='Finanzas', index=False)
            df_empleados.to_excel(writer, sheet_name='Empleados', index=False)
            df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
            df_proveedores.to_excel(writer, sheet_name='Proveedores', index=False)
            df_lotes.to_excel(writer, sheet_name='Lotes', index=False)
        
        st.download_button(
            label="📥 Descargar Base Completa (Excel)",
            data=buffer.getvalue(),
            file_name=f"Respaldo_Rancho_AE_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
    except Exception:
        pass
