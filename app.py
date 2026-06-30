import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

# ==========================================
# BARRA LATERAL: CONFIGURACIÓN Y LOGO
# ==========================================
with st.sidebar:
    st.header("🏢 Imagen Corporativa")
    logo_url = st.text_input(
        "URL del Logotipo de la Empresa:",
        value="https://images.unsplash.com/photo-1516467508483-a7212febe31a?q=80&w=200&auto=format&fit=crop", 
        help="Pega aquí el enlace de internet de tu imagen (JPG/PNG)"
    )
    if logo_url:
        st.image(logo_url, width=150)
    
    st.markdown("---")
    st.header("⚙️ Copias de Seguridad")

# Título Principal con Logo Integrado
col_title, col_logo = st.columns([4, 1])
with col_title:
    st.title("🤠 Rancho AE: Sistema de Administración")
with col_logo:
    if logo_url:
        st.image(logo_url, width=100)

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

ingresos, egresos, balance_neto, por_cobrar, por_pagar = 0.0, 0.0, 0.0, 0.0, 0.0

if not df_finanzas.empty:
    df_finanzas['monto'] = pd.to_numeric(df_finanzas['monto'], errors='coerce').fillna(0.0)
    
    ingresos = df_finanzas[(df_finanzas['tipo'] == 'Ingreso') & (df_finanzas['estado_deuda'] == 'Pagado')]['monto'].sum()
    egresos = df_finanzas[(df_finanzas['tipo'] == 'Egreso') & (df_finanzas['estado_deuda'] == 'Pagado')]['monto'].sum()
    balance_neto = ingresos - egresos
    
    por_cobrar = df_finanzas[(df_finanzas['tipo'] == 'Ingreso') & (df_finanzas['estado_deuda'] == 'Pendiente')]['monto'].sum()
    por_pagar = df_finanzas[(df_finanzas['tipo'] == 'Egreso') & (df_finanzas['estado_deuda'] == 'Pendiente')]['monto'].sum()
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🟢 Ingresos Reales", f"${ingresos:,.2f}")
    m2.metric("🔴 Egresos Reales", f"${egresos:,.2f}")
    m3.metric("💰 Balance Neto Actual", f"${balance_neto:,.2f}", delta=f"${balance_neto:,.2f}" if balance_neto >= 0 else f"${balance_neto:,.2f}", delta_color="normal" if balance_neto >= 0 else "inverse")
    m4.metric("📈 Por Cobrar (Clientes)", f"${por_cobrar:,.2f}")
    m5.metric("📉 Por Pagar (Proveedores)", f"${por_pagar:,.2f}")
    
    st.markdown("### 📝 Exportar Estado de Cuenta Oficial")
    if st.button("📄 Compilar Plantilla Institucional con Logotipo"):
        html_template = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.25; color: #333333;">
            <table style="width: 100%; border-bottom: 2px solid #5c4033; padding-bottom: 10px;">
                <tr>
                    <td style="width: 70%;">
                        <h1 style="margin: 0; color: #5c4033;">RANCHO AE</h1>
                        <p style="margin: 4px 0; font-style: italic; color: #666666;">Desarrollo Genético y Engorda Comercial</p>
                        <p style="margin: 2px 0; font-size: 11pt;"><strong>Reporte Consolidado de Administración</strong></p>
                    </td>
                    <td style="width: 30%; text-align: right;">
                        <img src="{logo_url}" style="width: 120px; max-height: 120px; object-fit: contain;" alt="Logo Empresa">
                    </td>
                </tr>
            </table>
            
            <br>
            <p><strong>Fecha de Emisión:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p>Este informe detalla el estado financiero integral extraído de forma segura desde los servidores de administración.</p>
            
            <h2 style="color: #5c4033; border-left: 4px solid #5c4033; padding-left: 8px;">1. Resumen de Saldos Monetarios</h2>
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%; border: 1px solid #dddddd;">
                <thead>
                    <tr style="background-color: #f8f9fa; text-align: left;">
                        <th>Concepto Operativo</th>
                        <th>Monto en Cuenta</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>🟢 Ingresos Consolidados (Liquidados)</td><td><strong>${ingresos:,.2f}</strong></td></tr>
                    <tr><td>🔴 Egresos Consolidados (Liquidados)</td><td><strong>${egresos:,.2f}</strong></td></tr>
                    <tr style="background-color: #f1f3f5;"><td><strong>💰 Balance Neto Comercial</strong></td><td><strong style="color: {'#2b8a3e' if balance_neto >= 0 else '#c92a2a'};">${balance_neto:,.2f}</strong></td></tr>
                    <tr><td>📈 Cuentas Pendientes de Cobro</td><td>${por_cobrar:,.2f}</td></tr>
                    <tr><td>📉 Cuentas Pendientes de Pago</td><td>${por_pagar:,.2f}</td></tr>
                </tbody>
            </table>
            
            <br>
            <h2 style="color: #5c4033; border-left: 4px solid #5c4033; padding-left: 8px;">2. Libro Diario Reciente</h2>
        """
        
        if not df_finanzas.empty:
            html_template += """
            <table border="1" cellpadding="6" style="border-collapse: collapse; width: 100%; border: 1px solid #dddddd; font-size: 10pt;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th>ID Código</th><th>Fecha</th><th>Tipo</th><th>Categoría</th><th>Concepto</th><th>Monto</th><th>Estado</th>
                    </tr>
                </thead>
                <tbody>
            """
            for _, r in df_finanzas.head(15).iterrows():
                html_template += f"""
                <tr>
                    <td>{r.get('id','')}</td>
                    <td>{r.get('fecha','')}</td>
                    <td>{r.get('tipo','')}</td>
                    <td>{r.get('categoria','')}</td>
                    <td>{r.get('concepto','')}</td>
                    <td>${float(r.get('monto',0)):,.2f}</td>
                    <td style="color: {'#2b8a3e' if r.get('estado_deuda')=='Pagado' else '#e67e22'}; font-weight: bold;">{r.get('estado_deuda','')}</td>
                </tr>
                """
            html_template += "</tbody></table>"
        
        html_template += """
            <br><br>
            <table style="width: 100%; margin-top: 40px; text-align: center; font-size: 11pt;">
                <tr>
                    <td style="width: 50%;">___________________________________<br>Dirección General de Operaciones</td>
                    <td style="width: 50%;">___________________________________<br>Control Interno y Auditoría</td>
                </tr>
            </table>
        </div>
        """
        st.session_state["reporte_html"] = html_template
        st.session_state["mostrar_descarga"] = True
        st.success("¡Estructura de la plantilla con logotipo lista para ser exportada!")

    if st.session_state["mostrar_descarga"]:
        with st.expander("👁️ Previsualizar Formato HTML del Documento"):
            # CORREGIDO AQUÍ: unsafe_allow_html=True
            st.markdown(st.session_state["reporte_html"], unsafe_allow_html=True)
else:
    st.info("💡 Registra movimientos en la pestaña de finanzas para generar el balance corporativo.")

st.markdown("---")

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
            f_cat = st.text_input("Categoría (Ej: Alimento, Venta Animales)")
            f_concepto = st.text_input("Concepto / Descripción")
        with col2:
            f_monto = st.number_input("Monto total ($)", min_value=0.0, step=100.0)
            f_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Cheque", "Crédito"])
            opciones_lotes = ["Ninguno"]
            if not df_lotes.empty and 'nombre_lote' in df_lotes.columns:
                opciones_lotes += list(df_lotes['nombre_lote'].dropna().unique())
            f_lote = st.selectbox("Lote Asociado", opciones_lotes)
            f_estado = st.selectbox("Estado del Pago", ["Pagado", "Pendiente"])
            f_venc = st.date_input("Fecha Vencimiento", datetime.today()).strftime('%Y-%m-%d')
            
        if st.form_submit_button("💾 Guardar Transacción"):
            auto_id = f"TRA-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 100000}"
            nuevo_registro = {
                "id": auto_id, "fecha": f_fecha, "tipo": f_tipo, "categoria": f_cat,
                "concepto": f_concepto, "monto": float(f_monto), "metodo_pago": f_pago,
                "lote_asociado": f_lote, "estado_deuda": f_estado, "fecha_vencimiento": f_venc
            }
            if guardar_registro("finanzas", nuevo_registro, "id"):
                st.success(f"¡Transacción registrada con ID: {auto_id}!")
                st.session_state["mostrar_descarga"] = False
                st.rerun()

    st.markdown("### Historial de Movimientos")
    if not df_finanzas.empty:
        df_finanzas = df_finanzas.reindex(columns=["id", "fecha", "tipo", "categoria", "concepto", "monto", "metodo_pago", "lote_asociado", "estado_deuda", "fecha_vencimiento"])
    st.dataframe(df_finanzas, use_container_width=True, hide_index=True)

    if not df_finanzas.empty:
        st.markdown("#### 🛠️ Modificar o Eliminar Transacción")
        id_seleccionado = st.selectbox("Selecciona ID a alterar:", df_finanzas['id'].unique(), key="del_fin")
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
                    st.session_state["mostrar_descarga"] = False
                    st.rerun()
            if st.button("🗑️ Eliminar Registro", key="btn_del_fin"):
                if eliminar_registro("finanzas", "id", id_seleccionado):
                    st.warning("Registro eliminado.")
                    st.session_state["mostrar_descarga"] = False
                    st.rerun()

# Pestañas operativas
with tabs[1]:
    st.subheader("Administración de Personal")
    with st.form("form_empleados", clear_on_submit=True):
        e_nombre = st.text_input("Nombre del Empleado")
        e_tel = st.text_input("Teléfono")
        e_puesto = st.text_input("Puesto")
        if st.form_submit_button("💾 Guardar Empleado"):
            if e_nombre.strip() and guardar_registro("empleados", {"nombre": e_nombre.strip(), "telefono": e_tel, "puesto_funcion": e_puesto, "fecha_ingreso": datetime.today().strftime('%Y-%m-%d')}, "nombre"):
                st.rerun()
    st.dataframe(df_empleados, use_container_width=True, hide_index=True)
    if not df_empleados.empty:
        emp_sel = st.selectbox("Selecciona Empleado para Eliminar:", df_empleados['nombre'].unique())
        if st.button("
