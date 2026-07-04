import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import time
import plotly.express as px  # <-- Nueva librería para replicar las gráficas premium

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
        type=["png", "jpg", "jpeg"]
    )
    
    if logo_file is not None:
        try:
            bytes_data = logo_file.getvalue()
            st.image(bytes_data, width=150, caption="Logotipo cargado")
        except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")
    
    st.markdown("---")
    st.header("⚙️ Copias de Seguridad")

# Encabezado principal limpio
st.title("Rancho AE: Sistema de Administración Financiera")
st.markdown("---")

# ==========================================
# 2. VALIDACIÓN Y CONEXIÓN A SUPABASE
# ==========================================
if "supabase" not in st.secrets:
    st.warning("⚠️ Conexión pendiente: Configura Supabase en los Secrets.")
    st.stop()

from supabase import create_client, Client

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase: Client = init_connection()

def cargar_tabla(nombre_tabla):
    try:
        response = supabase.table(nombre_tabla).select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def guardar_registro(nombre_tabla, datos, llave_primaria):
    try:
        supabase.table(nombre_tabla).upsert(datos, on_conflict=llave_primaria).execute()
        return True
    except Exception:
        return False

def eliminar_registro(nombre_tabla, columna_llave, valor_llave):
    try:
        supabase.table(nombre_tabla).delete().eq(columna_llave, valor_llave).execute()
        return True
    except Exception:
        return False

# Carga global de datos
df_finanzas = cargar_tabla("finanzas")
df_empleados = cargar_tabla("empleados")
df_clientes = cargar_tabla("clientes")
df_proveedores = cargar_tabla("proveedores")
df_lotes = cargar_tabla("lotes")

# ==========================================
# FUNCIONES DE FORMATO VISUAL
# ==========================================
def colorear_filas_finanzas(row):
    if row['tipo'] == 'Ingreso':
        return ['background-color: rgba(46, 204, 113, 0.12); color: #2ecc71; font-weight: bold;'] * len(row)
    elif row['tipo'] == 'Egreso':
        return ['background-color: rgba(231, 76, 60, 0.08); color: #e74c3c;'] * len(row)
    return [''] * len(row)

# Procesamiento de números para las métricas del Tablero
if not df_finanzas.empty:
    df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
    df_finanzas['fecha'] = pd.to_datetime(df_finanzas['fecha'], errors='coerce')
    df_finanzas = df_finanzas.dropna(subset=['fecha'])
    
    # Valores globales del período seleccionado
    ingresos = df_finanzas[(df_finanzas['tipo'] == 'Ingreso') & (df_finanzas['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_finanzas[(df_finanzas['tipo'] == 'Egreso') & (df_finanzas['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    por_cobrar = df_finanzas[(df_finanzas['tipo'] == 'Ingreso') & (df_finanzas['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_finanzas[(df_finanzas['tipo'] == 'Egreso') & (df_finanzas['estado_deuda'] == 'Pendiente')]['monto'].sum()
else:
    ingresos, egresos, balance_neto, por_cobrar, por_pagar = 0, 0, 0, 0, 0

# ==========================================
# REESTRUCTURACIÓN DE LA INTERFAZ (ESTILO IMAGE_BCAE66.JPG)
# ==========================================

# ------------------------------------------
# FILA SUPERIOR: TARJETAS Y MINIGRÁFICAS (Métricas de Impacto)
# ------------------------------------------
st.markdown("### 📊 Tablero de Control Ejecutivo")
fila_tarjetas = st.columns([1.2, 1, 1.3], gap="medium")

with fila_tarjetas[0]:
    # Tarjeta 1: Dona de Distribución (Balance)
    with st.container(border=True):
        st.markdown("**Distribución de Capital (Balance)**")
        if ingresos > 0 or egresos > 0:
            df_pie = pd.DataFrame({"Tipo": ["Ingresos", "Egresos"], "Monto": [ingresos, egresos]})
            fig_pie = px.pie(df_pie, values="Monto", names="Tipo", hole=0.6,
                             color="Tipo", color_discrete_map={"Ingresos": "#2ecc71", "Egresos": "#e74c3c"})
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=140, showlegend=False,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
        else:
            st.caption("Sin transacciones pagadas")
        st.markdown(f"<h4 style='text-align: center; margin:0;'>Neto: ${balance_neto:,.2f}</h4>", unsafe_html=True)

with fila_tarjetas[1]:
    # Tarjeta 2: Resumen en Bloque Único ("My Cards" en la imagen)
    with st.container(border=True):
        st.markdown("**Capital en Caja Rancho AE**")
        st.markdown(f"<h2 style='color:#2ecc71; margin-top:15px;'>${balance_neto:,.2f}</h2>", unsafe_html=True)
        st.caption("Fondos reales liquidados disponibles")
        st.write("")
        st.markdown(f"📈 **Por Cobrar:** ${por_cobrar:,.2f} | 📉 **Por Pagar:** ${por_pagar:,.2f}")

with fila_tarjetas[2]:
    # Tarjeta 3: Gráfica de Tendencia Temporal (Spending de la imagen)
    with st.container(border=True):
        st.markdown("**Tendencia del Flujo de Efectivo**")
        if not df_finanzas.empty:
            df_linea = df_finanzas.copy()
            df_linea['Fecha'] = df_linea['fecha'].dt.date
            df_tendencia = df_linea.groupby(['Fecha', 'tipo'])['monto'].sum().unstack().fillna(0.0).reset_index()
            if 'Ingreso' not in df_tendencia.columns: df_tendencia['Ingreso'] = 0.0
            if 'Egreso' not in df_tendencia.columns: df_tendencia['Egreso'] = 0.0
            
            fig_line = px.line(df_tendencia, x="Fecha", y=["Ingreso", "Egreso"],
                               color_discrete_map={"Ingreso": "#2ecc71", "Egreso": "#e74c3c"})
            fig_line.update_layout(margin=dict(t=5, b=5, l=5, r=5), height=130, showlegend=False,
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig_line.update_xaxes(visible=False)
            fig_line.update_yaxes(visible=False)
            st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
        else:
            st.caption("Esperando datos históricos...")
        st.markdown(f"<p style='text-align: center; font-size:12px; margin:0;'>Ingresos (Verde) vs Egresos (Rojo)</p>", unsafe_html=True)

st.write("---")

# ------------------------------------------
# CUERPO CENTRAL: PESTAÑAS OPERATIVAS DIVIDIDAS EN COLUMNAS
# ------------------------------------------
tabs = st.tabs(["📊 Finanzas", "🤠 Empleados", "🤝 Clientes", "🚜 Proveedores", "🐂 Lotes"])

# PESTAÑA FINANZAS (Estructura de Dos Columnas de image_bcae66.jpg)
with tabs[0]:
    col_izq_form, col_der_tabla = st.columns([1, 2], gap="large")
    
    with col_izq_form:
        st.markdown("### 📥 Registro de Movimiento")
        with st.form("form_finanzas", clear_on_submit=True):
            f_fecha = st.date_input("Fecha Transacción", datetime.today()).strftime('%Y-%m-%d')
            f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta)").strip().upper()
            f_concepto = st.text_input("Concepto / Descripción").strip()
            f_monto = st.number_input("Monto total ($)", min_value=0.0, step=100.0)
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento", datetime.today()).strftime('%Y-%m-%d')
            
            if st.form_submit_button("💾 Guardar Transacción", use_container_width=True):
                auto_id = f"N-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000}"
                nuevo_registro = {
                    "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                    "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                    "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
                }
                if guardar_registro("finanzas", nuevo_registro, "id"):
                    st.success("¡Transacción Guardada!")
                    time.sleep(0.4)
                    st.rerun()

    with col_der_tabla:
        st.markdown("### 📋 Historial de Transacciones")
        buscar_fin = st.text_input("🔍 Filtrar historial en tiempo real...", placeholder="Escribe un concepto, categoría o lote...")
        
        if not df_finanzas.empty:
            df_vista_finanzas = df_finanzas.copy()
            df_vista_finanzas['fecha'] = df_vista_finanzas['fecha'].dt.strftime('%Y-%m-%d')
            df_vista_finanzas = df_vista_finanzas.reindex(columns=["id", "fecha", "tipo", "categoria", "concepto", "monto", "metodo_pago", "estado_deuda"])
            
            if buscar_fin:
                mascara = df_vista_finanzas.astype(str).apply(lambda x: x.str.contains(buscar_fin, case=False)).any(axis=1)
                df_vista_finanzas = df_vista_finanzas[mascara]
                
            if not df_vista_finanzas.empty:
                # El historial estilizado con filas completas usando el Styler nativo de Streamlit
                df_fin_estilizado = (df_vista_finanzas.style
                                     .apply(colorear_filas_finanzas, axis=1)
                                     .format({'monto': '${:,.2f}'}))
                st.dataframe(df_fin_estilizado, use_container_width=True, hide_index=True)
            else:
                st.info("No se encontraron transacciones.")
        
        # Panel de Modificación rápido al fondo de la tabla
        if not df_finanzas.empty:
            with st.expander("🛠️ Acciones de Edición y Eliminación Rápida"):
                id_seleccionado = st.selectbox("Selecciona ID de Transacción:", df_finanzas['id'].unique())
                fila_sel = df_finanzas[df_finanzas['id'] == id_seleccionado].iloc[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    nuevo_estado = st.selectbox("Cambiar Estado a:", ["Pagado", "Pendiente"], index=0 if fila_sel['estado_deuda'] == 'Pagado' else 1)
                with c2:
                    nuevo_monto = st.number_input("Corregir Monto ($):", min_value=0.0, value=float(fila_sel['monto']))
                
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("🔄 Actualizar Datos", use_container_width=True):
                        fila_sel['estado_deuda'] = nuevo_estado
                        fila_sel['monto'] = nuevo_monto
                        fila_sel['fecha'] = fila_sel['fecha'].strftime('%Y-%m-%d')
                        if guardar_registro("finanzas", fila_sel.to_dict(), "id"):
                            st.success("Modificado con éxito")
                            time.sleep(0.4)
                            st.rerun()
                with ce2:
                    if st.button("🗑️ Eliminar Transacción", use_container_width=True, type="primary"):
                        if eliminar_registro("finanzas", "id", id_seleccionado):
                            st.warning("Registro borrado")
                            time.sleep(0.4)
                            st.rerun()

# PESTAÑAS ADICIONALES (Mantenidas limpias e independientes)
with tabs[1]:
    st.subheader("Personal del Rancho")
    st.dataframe(df_empleados, use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Registro de Clientes")
    st.dataframe(df_clientes, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Catálogo de Proveedores")
    st.dataframe(df_proveedores, use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("Control de Lotes de Ganado")
    st.dataframe(df_lotes, use_container_width=True, hide_index=True)

# Descarga de Respaldo Excel General en la Barra Lateral
with st.sidebar:
    if not df_finanzas.empty:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_finanzas.to_excel(writer, sheet_name='Finanzas', index=False)
                df_empleados.to_excel(writer, sheet_name='Empleados', index=False)
            st.download_button(
                label="📥 Descargar Respaldo Excel", data=buffer.getvalue(),
                file_name=f"Respaldo_Rancho_AE_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.ms-excel", use_container_width=True
            )
        except Exception:
            pass
