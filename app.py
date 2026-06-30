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
    st.markdown("""
    ### ⚙️ Configuración requerida en los Secrets de Streamlit Cloud:
    ```toml
    [supabase]
    url = "https://tu_proyecto_id.supabase.co"
    key = "tu_llave_anon_public_aqui"
    ```
    """)
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

# Funciones de carga y guardado optimizadas con control de autenticación
def cargar_tabla(nombre_tabla):
    try:
        response = supabase.table(nombre_tabla).select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        error_msg = str(e)
        # Captura limpia de la clave API inválida (Error 401)
        if "401" in error_msg or "Invalid API key" in error_msg:
            st.error("❌ **Llave API Inválida (Error 401):** La contraseña secreta (`key`) en tus Secrets de Streamlit es incorrecta. Por favor, ve a Supabase -> Project Settings -> API, copia la llave **'anon public'** y reemplázala en Streamlit Cloud.")
            st.stop()
        elif "Name or service not known" in error_msg or "Failed to resolve" in error_msg:
            st.error(f"❌ Error de red: La URL '{st.secrets['supabase']['url']}' no es válida. Revísala en tus Secrets.")
            st.stop()
        else:
            st.error(f"Error al leer la tabla {nombre_tabla}: {e}")
        return pd.DataFrame()

def guardar_registro(nombre_tabla, datos, llave_primaria):
    try:
        supabase.table(nombre_tabla).upsert(datos, on_conflict=llave_primaria).execute()
        return True
    except Exception as e:
        st.error(f"Error crítico al guardar en {nombre_tabla}: {e}")
        return False

# Cargar los datos actuales directamente de la nube de forma segura
df_finanzas = cargar_tabla("finanzas")
df_empleados = cargar_tabla("empleados")
df_clientes = cargar_tabla("clientes")
df_proveedores = cargar_tabla("proveedores")
df_lotes = cargar_tabla("lotes")

# ==========================================
# 4. INTERFAZ PRINCIPAL POR PESTAÑAS
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# ------------------------------------------
# PESTAÑA 1: FINANZAS
# ------------------------------------------
with tabs[0]:
    st.subheader("Registro y Control Financiero")
    
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            f_id = st.text_input("ID Transacción (Único)")
            f_fecha = st.date_input("Fecha", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
        with col2:
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta, Medicina)")
            f_concepto = st.text_input("Concepto / Descripción")
            f_monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        with col3:
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            
            f_estado = st.selectbox("Estado Deuda", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Transacción"):
            if f_id.strip():
                nuevo_registro = {
                    "id": f_id.strip(), "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                    "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                    "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
                }
                if guardar_registro("finanzas", nuevo_registro, "id"):
                    st.success("¡Transacción guardada en la nube de forma permanente!")
                    st.rerun()
            else:
                st.error("Por favor, asigna un ID único a la transacción.")

    st.markdown("### Historial de Movimientos")
    if not df_finanzas.empty:
        columnas_orden = ["id", "fecha", "tipo", "categoria", "concepto", "monto", "metodo_pago", "lote_asociado", "estado_deuda", "fecha_vencimiento"]
        df_finanzas = df_finanzas.reindex(columns=columnas_orden)
    st.dataframe(df_finanzas, use_container_width=True, hide_index=True)

# ------------------------------------------
# PESTAÑA 2: EMPLEADOS
# ------------------------------------------
with tabs[1]:
    st.subheader("Administración de Personal")
    
    with st.form("form_empleados", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            e_nombre = st.text_input("Nombre Completo del Empleado")
            e_tel = st.text_input("Teléfono de Contacto")
        with col2:
            e_puesto = st.text_input("Puesto / Función del Empleado")
            e_ingreso = st.date_input("Fecha de Ingreso", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre.strip():
                nuevo_registro = {
                    "nombre": e_nombre.strip(), "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": e_ingreso
                }
                if guardar_registro("empleados", nuevo_registro, "nombre"):
                    st.success(f"¡Datos de {e_nombre} sincronizados!")
                    st.rerun()
            else:
                st.error("El nombre es obligatorio.")

    st.markdown("### Plantilla Activa")
    st.dataframe(df_empleados, use_container_width=True, hide_index=True)

# ------------------------------------------
# PESTAÑA 3: CLIENTES
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
            c_notas = st.text_area("Notas / Condiciones Comerciales")
            
        if st.form_submit_button("💾 Guardar Cliente"):
            if c_nombre.strip():
                nuevo_registro = {
                    "nombre_razon": c_nombre.strip(), "contacto": c_contacto, "telefono": c_tel, "notas": c_notas
                }
                if guardar_registro("clientes", nuevo_registro, "nombre_razon"):
                    st.success("¡Cliente respaldado con éxito!")
                    st.rerun()
            else:
                st.error("El nombre o razón social es requerido.")

    st.markdown("### Directorio de Clientes")
    st.dataframe(df_clientes, use_container_width=True, hide_index=True)

# ------------------------------------------
# PESTAÑA 4: PROVEEDORES
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
            p_insumo = st.text_input("Insumo Principal (Ej: Alimentos, Medicinas)")
            
        if st.form_submit_button("💾 Guardar Proveedor"):
            if p_nombre.strip():
                nuevo_registro = {
                    "nombre_proveedor": p_nombre.strip(), "contacto": p_contacto, "telefono": p_tel, "insumo_principal": p_insumo
                }
                if guardar_registro("proveedores", nuevo_registro, "nombre_proveedor"):
                    st.success("¡Proveedor guardado correctamente!")
                    st.rerun()
            else:
                st.error("El nombre del proveedor es obligatorio.")

    st.markdown("### Lista de Proveedores Autorizados")
    st.dataframe(df_proveedores, use_container_width=True, hide_index=True)

# ------------------------------------------
# PESTAÑA 5: LOTES
# ------------------------------------------
with tabs[4]:
    st.subheader("Control de Lotes de Ganado")
    
    with st.form("form_lotes", clear_on_submit=True):
        l_nombre = st.text_input("Nombre o Código del Lote (Ej: Lote_Sardo_01)")
        l_desc = st.text_area("Descripción del Lote")
        l_creacion = st.date_input("Fecha de Creación", datetime.today()).strftime('%Y-%m-%d')
        
        if st.form_submit_button("💾 Guardar Lote"):
            if l_nombre.strip():
                nuevo_registro = {
                    "nombre_lote": l_nombre.strip(), "descripcion_notas": l_desc, "fecha_creacion": l_creacion
                }
                if guardar_registro("lotes", nuevo_registro, "nombre_lote"):
                    st.success(f"¡Lote '{l_nombre}' registrado de forma permanente!")
                    st.rerun()
            else:
                st.error("El nombre del lote es obligatorio.")

    st.markdown("### Lotes Activos en el Rancho")
    st.dataframe(df_lotes, use_container_width=True, hide_index=True)

# ==========================================
# 5. BARRA LATERAL: RESPALDO EXCEL
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
        st.warning("Motor de reportes listo.")
