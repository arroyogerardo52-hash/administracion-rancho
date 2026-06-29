import streamlit as st
import pandas as pd
from datetime import datetime
import json
import io

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

st.title("🤠 Rancho AE: Sistema de Administración Nacio")
st.markdown("---")

# ==========================================
# 2. FUNCIONES DE ALMACENAMIENTO INTERNO (STREAMLIT CLOUD)
# ==========================================
def cargar_tabla_interna(nombre_tabla):
    try:
        # Lee la cadena JSON guardada en los secrets de Streamlit Cloud
        datos_json = st.secrets["datos_rancho"][nombre_tabla]
        lista_datos = json.loads(datos_json)
        return pd.DataFrame(lista_datos)
    except Exception:
        # Si está vacío o no se encuentra, regresa un DataFrame limpio
        return pd.DataFrame()

def guardar_tabla_interna(nombre_tabla, df):
    # Convierte el DataFrame a formato JSON y lo guarda de forma persistente en Streamlit Cloud
    st.secrets["datos_rancho"][nombre_tabla] = json.dumps(df.to_dict(orient="records"))

# Cargar los datos actuales al iniciar la aplicación
df_finanzas = cargar_tabla_interna("finanzas")
df_empleados = cargar_tabla_interna("empleados")
df_clientes = cargar_tabla_interna("clientes")
df_proveedores = cargar_tabla_interna("proveedores")
df_lotes = cargar_tabla_interna("lotes")

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
            f_id = st.text_input("ID Transacción (Único)")
            f_fecha = st.date_input("Fecha", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
        with col2:
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta, Medicina)")
            f_concepto = st.text_input("Concepto / Descripción")
            f_monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        with col3:
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            # Carga dinámica de lotes para asociar
            opciones_lotes = ["Ninguno"] + list(df_lotes['nombre_lote'].unique()) if not df_lotes.empty else ["Ninguno"]
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado Deuda", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento (Si aplica)", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Transacción"):
            if f_id:
                nuevo_registro = {
                    "id": f_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                    "concepto": f_concepto, "monto": f_monto, "metodo_pago": f_pago,
                    "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
                }
                
                if df_finanzas.empty:
                    df_nuevo = pd.DataFrame([nuevo_registro])
                else:
                    df_nuevo = pd.concat([df_finanzas, pd.DataFrame([nuevo_registro])], ignore_index=True)
                    df_nuevo = df_nuevo.drop_duplicates(subset=['id'], keep='last')
                
                guardar_tabla_interna("finanzas", df_nuevo)
                st.success("¡Transacción financiera guardada de forma permanente!")
                st.rerun()
            else:
                st.error("Por favor, asigna un ID único a la transacción.")

    st.markdown("### Historial de Movimientos")
    st.dataframe(df_finanzas, use_container_width=True)

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
            if e_nombre:
                nuevo_registro = {
                    "nombre": e_nombre, "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": e_ingreso
                }
                
                if df_empleados.empty:
                    df_nuevo = pd.DataFrame([nuevo_registro])
                else:
                    df_nuevo = pd.concat([df_empleados, pd.DataFrame([nuevo_registro])], ignore_index=True)
                    df_nuevo = df_nuevo.drop_duplicates(subset=['nombre'], keep='last')
                
                guardar_tabla_interna("empleados", df_nuevo)
                st.success(f"¡Datos de {e_nombre} actualizados con éxito!")
                st.rerun()
            else:
                st.error("El nombre es obligatorio.")

    st.markdown("### Plantilla Activa")
    st.dataframe(df_empleados, use_container_width=True)

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
            if c_nombre:
                nuevo_registro = {
                    "nombre_razon": c_nombre, "contacto": c_contacto, "telefono": c_tel, "notas": c_notas
                }
                
                if df_clientes.empty:
                    df_nuevo = pd.DataFrame([nuevo_registro])
                else:
                    df_nuevo = pd.concat([df_clientes, pd.DataFrame([nuevo_registro])], ignore_index=True)
                    df_nuevo = df_nuevo.drop_duplicates(subset=['nombre_razon'], keep='last')
                
                guardar_tabla_interna("clientes", df_nuevo)
                st.success("¡Cliente guardado exitosamente!")
                st.rerun()
            else:
                st.error("El nombre o razón social es requerido.")

    st.markdown("### Directorio de Clientes")
    st.dataframe(df_clientes, use_container_width=True)

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
            if p_nombre:
                nuevo_registro = {
                    "nombre_proveedor": p_nombre, "contacto": p_contacto, "telefono": p_tel, "insumo_principal": p_insumo
                }
                
                if df_proveedores.empty:
                    df_nuevo = pd.DataFrame([nuevo_registro])
                else:
                    df_nuevo = pd.concat([df_proveedores, pd.DataFrame([nuevo_registro])], ignore_index=True)
                    df_nuevo = df_nuevo.drop_duplicates(subset=['nombre_proveedor'], keep='last')
                
                guardar_tabla_interna("proveedores", df_nuevo)
                st.success("¡Proveedor almacenado correctamente!")
                st.rerun()
            else:
                st.error("El nombre del proveedor es obligatorio.")

    st.markdown("### Lista de Proveedores Autorizados")
    st.dataframe(df_proveedores, use_container_width=True)

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
            if l_nombre:
                nuevo_registro = {
                    "nombre_lote": l_nombre, "descripcion_notas": l_desc, "fecha_creacion": l_creacion
                }
                
                if df_lotes.empty:
                    df_nuevo = pd.DataFrame([nuevo_registro])
                else:
                    df_nuevo = pd.concat([df_lotes, pd.DataFrame([nuevo_registro])], ignore_index=True)
                    df_nuevo = df_nuevo.drop_duplicates(subset=['nombre_lote'], keep='last')
                
                guardar_tabla_interna("lotes", df_nuevo)
                st.success(f"¡Lote '{l_nombre}' registrado permanentemente!")
                st.rerun()
            else:
                st.error("El nombre del lote es obligatorio.")

    st.markdown("### Lotes Activos en el Rancho")
    st.dataframe(df_lotes, use_container_width=True)

# ==========================================
# 4. BARRA LATERAL: EXPORTACIÓN ADICIONAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Herramientas")
    st.markdown("Aunque tus datos ya están seguros dentro de Streamlit Cloud, puedes descargar una copia local en Excel cuando lo desees:")
    
    # Crear un excel con todas las pestañas juntas en memoria
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
