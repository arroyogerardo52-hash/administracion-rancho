import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

st.title("🤠 Rancho AE: Sistema de Administración")
st.markdown("---")

# Inicializar la conexión segura con la Base de Datos en la Nube
conn = st.connection("sql")

# ==========================================
# 2. INICIALIZACIÓN DE TABLAS EN LA NUBE
# ==========================================
def inicializar_base_de_datos():
    # Pestaña Finanzas
    conn.query("""
        CREATE TABLE IF NOT EXISTS finanzas (
            id TEXT PRIMARY KEY, fecha TEXT, tipo TEXT, categoria TEXT, 
            concepto TEXT, monto REAL, metodo_pago TEXT, lote_asociado TEXT, 
            estado_deuda TEXT, fecha_vencimiento TEXT
        );
    """, ttl=0)
    
    # Pestaña Empleados
    conn.query("""
        CREATE TABLE IF NOT EXISTS empleados (
            nombre TEXT PRIMARY KEY, telefono TEXT, puesto_funcion TEXT, fecha_ingreso TEXT
        );
    """, ttl=0)
    
    # Pestaña Clientes
    conn.query("""
        CREATE TABLE IF NOT EXISTS clientes (
            nombre_razon TEXT PRIMARY KEY, contacto TEXT, telefono TEXT, notas TEXT
        );
    """, ttl=0)
    
    # Pestaña Proveedores
    conn.query("""
        CREATE TABLE IF NOT EXISTS proveedores (
            nombre_proveedor TEXT PRIMARY KEY, contacto TEXT, telefono TEXT, insumo_principal TEXT
        );
    """, ttl=0)
    
    # Pestaña Lotes
    conn.query("""
        CREATE TABLE IF NOT EXISTS lotes (
            nombre_lote TEXT PRIMARY KEY, descripcion_notas TEXT, fecha_creacion TEXT
        );
    """, ttl=0)

# Asegurar la estructura de almacenamiento en la nube
inicializar_base_de_datos()

# ==========================================
# 3. FUNCIONES DE CARGA DE DATOS (READ)
# ==========================================
def cargar_tabla(tabla_nombre):
    try:
        return conn.query(f"SELECT * FROM {tabla_nombre};", ttl=0)
    except Exception:
        return pd.DataFrame()

df_finanzas = cargar_tabla("finanzas")
df_empleados = cargar_tabla("empleados")
df_clientes = cargar_tabla("clientes")
df_proveedores = cargar_tabla("proveedores")
df_lotes = cargar_tabla("lotes")

# ==========================================
# 4. MENÚ PRINCIPAL POR PESTAÑAS
# ==========================================
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# ------------------------------------------
# PESTAÑA: FINANZAS
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
            # Carga dinámica de lotes registrados para asociar de forma limpia
            opciones_lotes = ["Ninguno"] + list(df_lotes['nombre_lote'].unique()) if not df_lotes.empty else ["Ninguno"]
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado Deuda", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento (Si aplica)", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Transacción"):
            if f_id:
                q = """
                    INSERT INTO finanzas (id, fecha, tipo, categoria, concepto, monto, metodo_pago, lote_asociado, estado_deuda, fecha_vencimiento)
                    VALUES (:id, :fecha, :tipo, :cat, :concepto, :monto, :pago, :lote, :estado, :venc)
                    ON CONFLICT (id) DO UPDATE SET 
                        fecha=EXCLUDED.fecha, tipo=EXCLUDED.tipo, categoria=EXCLUDED.categoria, concepto=EXCLUDED.concepto,
                        monto=EXCLUDED.monto, metodo_pago=EXCLUDED.metodo_pago, lote_asociado=EXCLUDED.lote_asociado,
                        estado_deuda=EXCLUDED.estado_deuda, fecha_vencimiento=EXCLUDED.fecha_vencimiento;
                """
                conn.query(q, params={"id": f_id, "fecha": f_fecha, "tipo": f_tipo, "cat": f_cat, "concepto": f_concepto, "monto": f_monto, "pago": f_pago, "lote": f_lote, "estado": f_estado, "venc": f_venc}, ttl=0)
                st.success("¡Transacción financiera guardada de forma segura en la nube!")
                st.rerun()
            else:
                st.error("Por favor, asigna un ID único a la transacción.")

    st.markdown("### Historial de Movimientos")
    st.dataframe(df_finanzas, use_container_width=True)

# ------------------------------------------
# PESTAÑA: EMPLEADOS
# ------------------------------------------
with tabs[1]:
    st.subheader("Administración de Personal")
    
    with st.form("form_empleados", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            e_nombre = st.text_input("Nombre Completo del Empleado")
            e_tel = st.text_input("Teléfono de Contacto")
        with col2:
            e_puesto = st.text_input("Puesto / Función en el Rancho")
            e_ingreso = st.date_input("Fecha de Ingreso", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre:
                q = """
                    INSERT INTO empleados (nombre, telefono, puesto_funcion, fecha_ingreso)
                    VALUES (:nombre, :tel, :puesto, :ingreso)
                    ON CONFLICT (nombre) DO UPDATE SET 
                        telefono=EXCLUDED.telefono, puesto_funcion=EXCLUDED.puesto_funcion, fecha_ingreso=EXCLUDED.fecha_ingreso;
                """
                conn.query(q, params={"nombre": e_nombre, "tel": e_tel, "puesto": e_puesto, "ingreso": e_ingreso}, ttl=0)
                st.success(f"¡Datos de {e_nombre} guardados en la nube!")
                st.rerun()
            else:
                st.error("El nombre es obligatorio.")

    st.markdown("### Plantilla Activa")
    st.dataframe(df_empleados, use_container_width=True)

# ------------------------------------------
# PESTAÑA: CLIENTES
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
            if c_nombre:
                q = """
                    INSERT INTO clientes (nombre_razon, contacto, telefono, notas)
                    VALUES (:nombre, :contacto, :tel, :notas)
                    ON CONFLICT (nombre_razon) DO UPDATE SET 
                        contacto=EXCLUDED.contacto, telefono=EXCLUDED.telefono, notas=EXCLUDED.notas;
                """
                conn.query(q, params={"nombre": c_nombre, "contacto": c_contacto, "tel": c_tel, "notas": c_notas}, ttl=0)
                st.success("¡Cliente registrado!")
                st.rerun()
            else:
                st.error("El nombre o razón social es requerido.")

    st.markdown("### Directorio de Clientes")
    st.dataframe(df_clientes, use_container_width=True)

# ------------------------------------------
# PESTAÑA: PROVEEDORES
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
            p_insumo = st.text_input("Insumo Principal (Ej: Alimentos, Semillas, Medicinas)")
            
        if st.form_submit_button("💾 Guardar Proveedor"):
            if p_nombre:
                q = """
                    INSERT INTO proveedores (nombre_proveedor, contacto, telefono, insumo_principal)
                    VALUES (:nombre, :contacto, :tel, :insumo)
                    ON CONFLICT (nombre_proveedor) DO UPDATE SET 
                        contacto=EXCLUDED.contacto, telefono=EXCLUDED.telefono, insumo_principal=EXCLUDED.insumo_principal;
                """
                conn.query(q, params={"nombre": p_nombre, "contacto": p_contacto, "tel": p_tel, "insumo": p_insumo}, ttl=0)
                st.success("¡Proveedor guardado!")
                st.rerun()
            else:
                st.error("El nombre del proveedor es obligatorio.")

    st.markdown("### Lista de Proveedores Autorizados")
    st.dataframe(df_proveedores, use_container_width=True)

# ------------------------------------------
# PESTAÑA: LOTES
# ------------------------------------------
with tabs[4]:
    st.subheader("Control de Lotes de Ganado")
    
    with st.form("form_lotes", clear_on_submit=True):
        l_nombre = st.text_input("Nombre o Código del Lote (Ej: Lote_Sardo_01)")
        l_desc = st.text_area("Descripción / Notas del Lote (Origen, cabezas, tipo de engorda)")
        l_creacion = st.date_input("Fecha de Creación / Ingreso", datetime.today()).strftime('%Y-%m-%d')
        
        if st.form_submit_button("💾 Guardar Lote"):
            if l_nombre:
                q = """
                    INSERT INTO lotes (nombre_lote, descripcion_notas, fecha_creacion)
                    VALUES (:nombre, :desc, :creacion)
                    ON CONFLICT (nombre_lote) DO UPDATE SET 
                        descripcion_notas=EXCLUDED.descripcion_notas, fecha_creacion=EXCLUDED.fecha_creacion;
                """
                conn.query(q, params={"nombre": l_nombre, "desc": l_desc, "creacion": l_creacion}, ttl=0)
                st.success(f"¡Lote '{l_nombre}' registrado de forma permanente!")
                st.rerun()
            else:
                st.error("El nombre del lote es obligatorio.")

    st.markdown("### Lotes Activos en el Rancho")
    st.dataframe(df_lotes, use_container_width=True)


# ==========================================
# 5. BARRA LATERAL: RESPALDOS EXCEL ADICIONALES
# ==========================================
with st.sidebar:
    st.header("⚙️ Herramientas")
    st.markdown("Aunque tus datos están seguros en la nube de forma permanente, puedes descargar una copia en Excel cuando lo necesites:")
    
    # Crear un buffer en memoria para compilar el Excel completo
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_finanzas.to_excel(writer, sheet_name='Finanzas', index=False)
        df_empleados.to_excel(writer, sheet_name='Empleados', index=False)
        df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
        df_proveedores.to_excel(writer, sheet_name='Proveedores', index=False)
        df_lotes.to_excel(writer, sheet_name='Lotes', index=False)
    
    st.download_button(
        label="📥 Descargar todo en Excel",
        data=buffer.getvalue(),
        file_name=f"Respaldo_Total_Rancho_AE_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.ms-excel",
        use_container_width=True
    )
