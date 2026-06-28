import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la plataforma
st.set_page_config(page_title="Sistema Integral Rancho AE", layout="wide", page_icon="🤠")

# --- APARTADO DE IDENTIDAD CORPORATIVA (LOGO Y NOMBRE) ---
# Título principal de la empresa en la parte superior del cuerpo
st.title(" Rancho AE - Ganadería ")

# Recuadro en la barra lateral para personalizar el logotipo del rancho
st.sidebar.markdown("### 🏷️ Administracion ")
archivo_logo = st.sidebar.file_uploader("Subir logotipo de la empresa (PNG/JPG)", type=["png", "jpg", "jpeg"])

if archivo_logo is not None:
    # Si subes un logo, lo muestra en la barra lateral
    st.sidebar.image(archivo_logo, use_container_width=True)
else:
    # Imagen o aviso por defecto si aún no se ha subido un logo
    st.sidebar.info("💡 Consejo: Sube el logo de Rancho AE aquí arriba para personalizar tu plataforma.")

st.sidebar.markdown("---")

# --- DEFINICIÓN DE ARCHIVOS ---
ARCHIVOS = {
    'finanzas': 'administracion_rancho.csv',
    'empleados': 'empleados_rancho.csv',
    'clientes': 'clientes_rancho.csv',
    'proveedores': 'proveedores_rancho.csv',
    'lotes': 'lotes_rancho.csv'
}

# Columnas de las bases de datos
COL_FINANZAS = ['ID', 'Fecha', 'Tipo', 'Categoría', 'Concepto', 'Monto ($)', 'Método Pago', 'Lote Asociado', 'Estado Deuda', 'Fecha Vencimiento']
COL_EMPLEADOS = ['Nombre', 'Teléfono', 'Puesto / Función', 'Fecha Ingreso']
COL_CLIENTES = ['Nombre / Razón Social', 'Contacto', 'Teléfono', 'Notas']
COL_PROVEEDORES = ['Nombre Proveedor', 'Contacto', 'Teléfono', 'Insumo Principal']
COL_LOTES = ['Nombre del Lote', 'Descripción / Notas', 'Fecha Creación']

# Cargar o inicializar archivos
dfs = {}
for clave, archivo in ARCHIVOS.items():
    columnas = locals()[f"COL_{clave.upper()}"]
    if os.path.exists(archivo):
        dfs[clave] = pd.read_csv(archivo)
    else:
        dfs[clave] = pd.DataFrame(columns=columnas)

# --- MENÚ DE NAVEGACIÓN PRINCIPAL ---
st.sidebar.markdown("###  Operaciones")
opcion_menu = st.sidebar.radio("📋 MENÚ PRINCIPAL", [
    "📊 Panel Financiero y Balances",
    "💰 Registro de Movimientos y Deudas",
    "🐂 Control de Lotes de Ganado",
    "🤠 Gestión de Empleados",
    "🤝 Clientes y Ventas",
    "🚜 Proveedores e Insumos"
])

st.sidebar.markdown("---")

# ==========================================
# 1. PANEL FINANCIERO Y BALANCES
# ==========================================
if opcion_menu == "📊 Panel Financiero y Balances":
    st.header("📊 Resumen Ejecutivo y Flujo de Caja")
    
    df_f = dfs['finanzas']
    
    if not df_f.empty:
        df_f['Fecha'] = pd.to_datetime(df_f['Fecha'])
        df_f['Monto ($)'] = pd.to_numeric(df_f['Monto ($)'])
        
        # Filtro de Tiempo
        filtro_tiempo = st.selectbox("📅 Vista Temporal del Balance:", ["Total Histórico", "Anual (Año Actual)", "Mensual (Mes Actual)", "Semanal (Últimos 7 días)"])
        
        fecha_actual = datetime.now()
        if filtro_tiempo == "Anual (Año Actual)":
            df_filtrado = df_f[df_f['Fecha'].dt.year == fecha_actual.year]
        elif filtro_tiempo == "Mensual (Mes Actual)":
            df_filtrado = df_f[(df_f['Fecha'].dt.year == fecha_actual.year) & (df_f['Fecha'].dt.month == fecha_actual.month)]
        elif filtro_tiempo == "Semanal (Últimos 7 días)":
            df_filtrado = df_f[(fecha_actual - df_f['Fecha']).dt.days <= 7]
        else:
            df_filtrado = df_f

        # Cálculos de balances normales
        ingresos = df_filtrado[(df_filtrado['Tipo'] == 'Ingreso') & (df_filtrado['Estado Deuda'] == 'Liquidado')]['Monto ($)'].sum()
        gastos = df_filtrado[(df_filtrado['Tipo'] == 'Gasto') & (df_filtrado['Estado Deuda'] == 'Liquidado')]['Monto ($)'].sum()
        
        # Cálculos de Deudas
        por_cobrar = df_f[(df_f['Tipo'] == 'Ingreso') & (df_f['Estado Deuda'] == 'Por Cobrar')]['Monto ($)'].sum()
        por_pagar = df_f[(df_f['Tipo'] == 'Gasto') & (df_f['Estado Deuda'] == 'Por Pagar')]['Monto ($)'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("🟢 Ingresos Efectivos", f"${ingresos:,.2f}")
        col2.metric("🔴 Gastos Efectivos", f"${gastos:,.2f}")
        col3.metric("💰 Utilidad Real", f"${ingresos - gastos:,.2f}")
        
        st.markdown("### ⚠️ Control de Cuentas y Deudas")
        cold1, cold2 = st.columns(2)
        cold1.metric("📥 Total por Cobrar (Clientes)", f"${por_cobrar:,.2f}")
        cold2.metric("📤 Total por Pagar (Proveedores)", f"${por_pagar:,.2f}")
        
        # Pestañas de Análisis
        t1, t2, t3 = st.tabs(["📋 Libro de Movimientos", "📊 Gráficas de Rendimiento", "🔍 Análisis por Lote"])
        with t1:
            st.subheader("Historial de Transacciones Registradas")
            
            # Opción de Eliminar Movimiento
            st.markdown("#### 🗑️ Eliminar un registro por error")
            if not df_f.empty:
                id_eliminar = st.selectbox("Selecciona el ID del movimiento a borrar:", df_f['ID'].tolist())
                if st.button("❌ Eliminar Registro Seleccionado"):
                    df_f = df_f[df_f['ID'] != id_eliminar]
                    df_f.to_csv(ARCHIVOS['finanzas'], index=False)
                    st.success(f"Movimiento con ID {id_eliminar} eliminado con éxito.")
                    st.rerun()
            
            st.dataframe(df_filtrado.sort_values(by='Fecha', ascending=False), use_container_width=True)
            
        with t2:
            if not df_filtrado.empty:
                st.subheader("Distribución Financiera")
                cg1, cg2 = st.columns(2)
                with cg1:
                    st.markdown("**Gastos por Categoría:**")
                    g_cat = df_filtrado[df_filtrado['Tipo'] == 'Gasto'].groupby('Categoría')['Monto ($)'].sum()
                    if not g_cat.empty: st.bar_chart(g_cat)
                with cg2:
                    st.markdown("**Ingresos por Categoría:**")
                    i_cat = df_filtrado[df_filtrado['Tipo'] == 'Ingreso'].groupby('Categoría')['Monto ($)'].sum()
                    if not i_cat.empty: st.bar_chart(i_cat)
        with t3:
            st.subheader("Análisis de Costos/Ingresos por Lote de Ganado")
            lotes_existentes = ["Todos"] + dfs['lotes']['Nombre del Lote'].tolist()
            lote_sel = st.selectbox("Selecciona un lote para analizar:", lotes_existentes)
            if lote_sel != "Todos":
                df_lote = df_f[df_f['Lote Asociado'] == lote_sel]
                st.dataframe(df_lote, use_container_width=True)
                il = df_lote[df_lote['Tipo'] == 'Ingreso']['Monto ($)'].sum()
                gl = df_lote[df_lote['Tipo'] == 'Gasto']['Monto ($)'].sum()
                st.info(f"Ganancia Neta del Lote {lote_sel}: ${il - gl:,.2f}")
    else:
        st.info("No hay datos financieros registrados aún.")

# ==========================================
# 2. REGISTRO DE MOVIMIENTOS
# ==========================================
elif opcion_menu == "💰 Registro de Movimientos y Deudas":
    st.header("💰 Registrar Nueva Operación Financiera")
    
    with st.form("form_finanzas", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_c = st.date_input("Fecha de Operación", datetime.now())
            tipo_m = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"])
            
            # Categorías base + Opción Manual
            if tipo_m == "Ingreso":
                cat_base = ["Liquidación / Venta de Ganado", "Cobro de Fletes / Logística", "Venta de Forraje", "OTRA (Agregar de forma manual)"]
                cat_sel = st.selectbox("Categoría", cat_base)
            else:
                cat_base = ["Alimentación (Sorgo, pollinaza)", "Combustible (Diésel)", "Mantenimiento", "Salud Animal", "Nóminas", "OTRA (Agregar de forma manual)"]
                cat_sel = st.selectbox("Categoría", cat_base)
                
            if cat_sel == "OTRA (Agregar de forma manual)":
                categoria_final = st.text_input("Escribe la nueva categoría manual:")
            else:
                categoria_final = cat_sel

        with col_f2:
            concepto_c = st.text_input("Detalle / Concepto")
            monto_c = st.number_input("Monto ($)", min_value=0.0, step=100.0)
            
            # Métodos de Pago
            metodo_p = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta de Crédito/Débito", "Transferencia Bancaria", "Otro"])
            
            # Asociar a Lote de Ganado
            lista_lotes = ["Ninguno / Administración General"] + dfs['lotes']['Nombre del Lote'].tolist()
            lote_asoc = st.selectbox("Asociar este movimiento al Lote:", lista_lotes)
            
        st.markdown("---")
        st.markdown("#### 📆 Configuración de Créditos / Deudas")
        estado_d = st.selectbox("Estado del pago:", ["Liquidado", "Por Cobrar" if tipo_m == "Ingreso" else "Por Pagar"])
        fecha_venc = st.date_input("Fecha límite de cobro/pago (Si es deuda)", datetime.now())
        
        btn_guardar_f = st.form_submit_button("💾 Guardar Registro Contable")
        
    if btn_guardar_f:
        df_f = dfs['finanzas']
        nuevo_id = int(df_f['ID'].max() + 1) if not df_f.empty else 1000
        nueva_fila = pd.DataFrame([[
            nuevo_id, fecha_c.strftime('%Y-%m-%d'), tipo_m, categoria_final, concepto_c, monto_c, metodo_p, lote_asoc, estado_d, fecha_venc.strftime('%Y-%m-%d')
        ]], columns=COL_FINANZAS)
        
        df_f = pd.concat([df_f, nueva_fila], ignore_index=True)
        df_f.to_csv(ARCHIVOS['finanzas'], index=False)
        st.success("¡Movimiento contable guardado exitosamente!")

# ==========================================
# 3. CONTROL DE LOTES DE GANADO
# ==========================================
elif opcion_menu == "🐂 Control de Lotes de Ganado":
    st.header("🐂 Administración de Lotes de Ganado")
    
    col_l1, col_l2 = st.columns([1, 2])
    
    with col_l1:
        st.subheader("➕ Agregar Nuevo Lote")
        with st.form("form_lotes", clear_on_submit=True):
            nombre_lote = st.text_input("Nombre del Lote", placeholder="Ej. Lote Sardo Negro 2026")
            desc_lote = st.text_area("Descripción (Pesos iniciales, procedencia, etc.)")
            btn_lote = st.form_submit_button("Crear Lote")
            
        if btn_lote and nombre_lote.strip() != "":
            df_l = dfs['lotes']
            nueva_fila = pd.DataFrame([[nombre_lote, desc_lote, datetime.now().strftime('%Y-%m-%d')]], columns=COL_LOTES)
            df_l = pd.concat([df_l, nueva_fila], ignore_index=True)
            df_l.to_csv(ARCHIVOS['lotes'], index=False)
            st.success(f"Lote '{nombre_lote}' creado.")
            st.rerun()
            
    with col_l2:
        st.subheader("📋 Lotes Activos")
        if not dfs['lotes'].empty:
            st.dataframe(dfs['lotes'], use_container_width=True)
            
            st.markdown("#### ❌ Quitar Lote")
            lote_a_borrar = st.selectbox("Selecciona un lote para dar de baja:", dfs['lotes']['Nombre del Lote'].tolist())
            if st.button("Eliminar Lote definitivamente"):
                df_l = dfs['lotes']
                df_l = df_l[df_l['Nombre del Lote'] != lote_a_borrar]
                df_l.to_csv(ARCHIVOS['lotes'], index=False)
                st.warning(f"Lote '{lote_a_borrar}' eliminado.")
                st.rerun()
        else:
            st.info("No hay lotes registrados todavía.")

# ==========================================
# 4. GESTIÓN DE EMPLEADOS
# ==========================================
elif opcion_menu == "🤠 Gestión de Empleados":
    st.header("🤠 Personal y Miembros de la Empresa")
    
    col_e1, col_e2 = st.columns([1, 2])
    with col_e1:
        st.subheader("➕ Registrar Empleado")
        with st.form("form_emp", clear_on_submit=True):
            nom_emp = st.text_input("Nombre Completo")
            tel_emp = st.text_input("Número de Teléfono")
            puesto_emp = st.selectbox("Función / Puesto Asignado:", ["Chofer de Camión/Logística", "Caporal / Vaquero", "Administrador", "Encargado de Alimentos", "Otro"])
            btn_emp = st.form_submit_button("Registrar Empleado")
            
        if btn_emp and nom_emp.strip() != "":
            df_e = dfs['empleados']
            nueva_fila = pd.DataFrame([[nom_emp, tel_emp, puesto_emp, datetime.now().strftime('%Y-%m-%d')]], columns=COL_EMPLEADOS)
            df_e = pd.concat([df_e, nueva_fila], ignore_index=True)
            df_e.to_csv(ARCHIVOS['empleados'], index=False)
            st.success("Empleado registrado correctamente.")
            st.rerun()
            
    with col_e2:
        st.subheader("📋 Plantilla de Trabajo")
        if not dfs['empleados'].empty:
            st.dataframe(dfs['empleados'], use_container_width=True)
        else:
            st.info("Aún no tienes empleados registrados.")

# ==========================================
# 5. CLIENTES Y VENTAS
# ==========================================
elif opcion_menu == "🤝 Clientes y Ventas":
    st.header("🤝 Registro de Clientes Comerciales")
    
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        st.subheader("➕ Registrar Cliente")
        with st.form("form_cli", clear_on_submit=True):
            nom_cli = st.text_input("Nombre o Razón Social")
            cont_cli = st.text_input("Persona de Contacto")
            tel_cli = st.text_input("Teléfono de Contacto")
            notas_cli = st.text_input("¿Qué le vendemos? / Notas")
            btn_cli = st.form_submit_button("Guardar Cliente")
            
        if btn_cli and nom_cli.strip() != "":
            df_c = dfs['clientes']
            nueva_fila = pd.DataFrame([[nom_cli, cont_cli, tel_cli, notas_cli]], columns=COL_CLIENTES)
            df_c = pd.concat([df_c, nueva_fila], ignore_index=True)
            df_c.to_csv(ARCHIVOS['clientes'], index=False)
            st.success("Cliente guardado en catálogo.")
            st.rerun()
            
    with col_c2:
        st.subheader("📋 Directorio de Clientes")
        if not dfs['clientes'].empty:
            st.dataframe(dfs['clientes'], use_container_width=True)
        else:
            st.info("No hay clientes registrados.")

# ==========================================
# 6. PROVEEDORES E INSUMOS
# ==========================================
elif opcion_menu == "🚜 Proveedores e Insumos":
    st.header("🚜 Directorio de Proveedores")
    
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        st.subheader("➕ Registrar Proveedor")
        with st.form("form_prov", clear_on_submit=True):
            nom_prov = st.text_input("Nombre de la Empresa / Proveedor")
            cont_prov = st.text_input("Atendido por")
            tel_prov = st.text_input("Teléfono")
            ins_prov = st.selectbox("Insumo Principal que provee:", ["Alimento / Granos", "Diésel / Combustible", "Fierro / Refacciones", "Medicinas / Veterinaria", "Otros"])
            btn_prov = st.form_submit_button("Guardar Proveedor")
            
        if btn_prov and nom_prov.strip() != "":
            df_p = dfs['proveedores']
            nueva_fila = pd.DataFrame([[nom_prov, cont_prov, tel_prov, ins_prov]], columns=COL_PROVEEDORES)
            df_p = pd.concat([df_p, nueva_fila], ignore_index=True)
            df_p.to_csv(ARCHIVOS['proveedores'], index=False)
            st.success("Proveedor registrado.")
            st.rerun()
            
    with col_p2:
        st.subheader("📋 Lista de Proveedores Autorizados")
        if not dfs['proveedores'].empty:
            st.dataframe(dfs['proveedores'], use_container_width=True)
        else:
            st.info("No hay proveedores en la lista.")
