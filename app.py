import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import io

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

st.title("🤠 Rancho AE: Sistema de Administración")
st.markdown("---")

# ==========================================
# 2. CONFIGURACIÓN Y FUNCIONES DE SQLITE
# ==========================================
DB_NAME = "rancho_ae.db"

def inicializar_base_datos():
    """Crea las tablas de forma permanente si no existen al iniciar la app"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla Finanzas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS finanzas (
            id TEXT PRIMARY KEY,
            fecha TEXT,
            tipo TEXT,
            categoria TEXT,
            concepto TEXT,
            monto REAL,
            metodo_pago TEXT,
            lote_asociado TEXT,
            estado_deuda TEXT,
            fecha_vencimiento TEXT
        )
    """)
    
    # Tabla Empleados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            nombre TEXT PRIMARY KEY,
            telefono TEXT,
            puesto_funcion TEXT,
            fecha_ingreso TEXT
        )
    """)
    
    # Tabla Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            nombre_razon TEXT PRIMARY KEY,
            contacto TEXT,
            telefono TEXT,
            notas TEXT
        )
    """)
    
    # Tabla Proveedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            nombre_proveedor TEXT PRIMARY KEY,
            contacto TEXT,
            telefono TEXT,
            insumo_principal TEXT
        )
    """)
    
    # Tabla Lotes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            nombre_lote TEXT PRIMARY KEY,
            descripcion_notas TEXT,
            fecha_creacion TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def ejecutar_query(query, params=(), retornar_df=False):
    """Función segura para leer o escribir datos sin conflictos"""
    conn = sqlite3.connect(DB_NAME)
    resultado = None
    try:
        if retornar_df:
            resultado = pd.read_sql_query(query, conn)
        else:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
    except Exception as e:
        st.error(f"Error en la base de datos: {e}")
    finally:
        conn.close()
    return resultado

# Asegurar que las tablas existan antes de renderizar la página
inicializar_base_datos()

# Cargar los datos actuales en DataFrames mediante consultas SQL limpias
df_finanzas = ejecutar_query("SELECT * FROM finanzas", retornar_df=True)
df_empleados = ejecutar_query("SELECT * FROM empleados", retornar_df=True)
df_clientes = ejecutar_query("SELECT * FROM clientes", retornar_df=True)
df_proveedores = ejecutar_query("SELECT * FROM proveedores", retornar_df=True)
df_lotes = ejecutar_query("SELECT * FROM lotes", retornar_df=True)

# ==========================================
# 3. INTERFAZ PRINCIPAL POR PESTAÑAS
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
            f_id = st.text_input("ID Transacción (Único - Clave para evitar pérdidas)")
            f_fecha = st.date_input("Fecha", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
        with col2:
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta, Medicina)")
            f_concepto = st.text_input("Concepto / Descripción")
            f_monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        with col3:
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            
            # Carga dinámica y segura de los lotes guardados en la base de datos
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            
            f_estado = st.selectbox("Estado Deuda", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento (Si aplica)", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Transacción"):
            if f_id.strip():
                # INSERT OR REPLACE asegura que si el ID ya existe, actualiza el registro en vez de fallar o duplicar
                query = """
                    INSERT OR REPLACE INTO finanzas 
                    (id, fecha, tipo, categoria, concepto, monto, metodo_pago, lote_asociado, estado_deuda, fecha_vencimiento)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                valores = (f_id.strip(), f_fecha, f_tipo, f_cat, f_concepto, f_monto, f_pago, f_lote, f_estado, f_venc)
                ejecutar_query(query, valores)
                st.success("¡Transacción financiera guardada de forma permanente en la base de datos!")
                st.rerun()
            else:
                st.error("Por favor, asigna un ID único a la transacción.")

    st.markdown("### Historial de Movimientos")
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
            e_puesto = st.text_input("Puesto / Función en el Rancho")
            e_ingreso = st.date_input("Fecha de Ingreso", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre.strip():
                query = "INSERT OR REPLACE INTO empleados (nombre, telefono, puesto_funcion, fecha_ingreso) VALUES (?, ?, ?, ?)"
                ejecutar_query(query, (e_nombre.strip(), e_tel, e_puesto, e_ingreso))
                st.success(f"¡Datos de {e_nombre} actualizados con éxito!")
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
                query = "INSERT OR REPLACE INTO clientes (nombre_razon, contacto, telefono, notas) VALUES (?, ?, ?, ?)"
                ejecutar_query(query, (c_nombre.strip(), c_contacto, c_tel, c_notas))
                st.success("¡Cliente guardado exitosamente!")
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
                query = "INSERT OR REPLACE INTO proveedores (nombre_proveedor, contacto, telefono, insumo_principal) VALUES (?, ?, ?, ?)"
                ejecutar_query(query, (p_nombre.strip(), p_contacto, p_tel, p_insumo))
                st.success("¡Proveedor almacenado correctamente!")
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
        l_desc = st.text_area("Descripción del Lote (Cabezas, tipo de engorda, procedencia)")
        l_creacion = st.date_input("Fecha de Creación", datetime.today()).strftime('%Y-%m-%d')
        
        if st.form_submit_button("💾 Guardar Lote"):
            if l_nombre.strip():
                query = "INSERT OR REPLACE INTO lotes (nombre_lote, descripcion_notas, fecha_creacion) VALUES (?, ?, ?)"
                ejecutar_query(query, (l_nombre.strip(), l_desc, l_creacion))
                st.success(f"¡Lote '{l_nombre}' registrado permanentemente!")
                st.rerun()
            else:
                st.error("El nombre del lote es obligatorio.")

    st.markdown("### Lotes Activos en el Rancho")
    st.dataframe(df_lotes, use_container_width=True, hide_index=True)

# ==========================================
# 4. BARRA LATERAL: RESPALDO Y EXPORTACIÓN
# ==========================================
with st.sidebar:
    st.header("⚙️ Herramientas")
    st.markdown("Tu información se escribe directamente en la base de datos interna de la app de forma segura.")
    st.markdown("Puedes descargar un respaldo completo en Excel de todas tus tablas aquí:")
    
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
