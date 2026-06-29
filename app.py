import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuración de la plataforma
st.set_page_config(page_title="Sistema Integral Rancho AE", layout="wide", page_icon="🤠")

# --- APARTADO DE IDENTIDAD CORPORATIVA (LOGO Y NOMBRE) ---
st.title("🤠 Rancho AE - Ganadería y Logística")

st.sidebar.markdown("### 🏷️ Identidad del Rancho")
archivo_logo = st.sidebar.file_uploader("Subir logotipo de la empresa (PNG/JPG)", type=["png", "jpg", "jpeg"])

if archivo_logo is not None:
    st.sidebar.image(archivo_logo, use_container_width=True)
else:
    st.sidebar.info("💡 Consejo: Sube el logo de Rancho AE aquí arriba para personalizar tu plataforma.")

st.sidebar.markdown("---")

# --- CONFIGURACIÓN DE CONEXIÓN A GOOGLE DRIVE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ENLACE DE TU HOJA CENTRAL
URL_HOJA_CENTRAL = "https://docs.google.com/spreadsheets/d/104btFARXhOW248PmFZyflsJjno9YIQJKHGFDrVGq6Fo/edit?usp=sharing"

# Nombres exactos de las pestañas en tu Google Sheets
PESTANAS = {
    'finanzas': 'Finanzas',
    'empleados': 'Empleados',
    'clientes': 'Clientes',
    'proveedores': 'Proveedores',
    'lotes': 'Lotes'
}

# Columnas de las bases de datos
COL_FINANZAS = ['ID', 'Fecha', 'Tipo', 'Categoría', 'Concepto', 'Monto ($)', 'Método Pago', 'Lote Asociado', 'Estado Deuda', 'Fecha Vencimiento']
COL_EMPLEADOS = ['Nombre', 'Teléfono', 'Puesto / Función', 'Fecha Ingreso']
COL_CLIENTES = ['Nombre / Razón Social', 'Contacto', 'Teléfono', 'Notas']
COL_PROVEEDORES = ['Nombre Proveedor', 'Contacto', 'Teléfono', 'Insumo Principal']
COL_LOTES = ['Nombre del Lote', 'Descripción / Notas', 'Fecha Creación']

# CARGAR DATOS DESDE LA NUBE EN TIEMPO REAL
dfs = {}
for clave, nombre_pestana in PESTANAS.items():
    columnas = locals()[f"COL_{clave.upper()}"]
    try:
        dfs[clave] = conn.read(spreadsheet=URL_HOJA_CENTRAL, worksheet=nombre_pestana)
        dfs[clave] = dfs[clave].dropna(how='all') # Limpiar renglones vacíos
        
        # Verificar que todas las columnas necesarias existan, si no, forzar estructura limpia
        for col in columnas:
            if col not in dfs[clave].columns:
                dfs[clave][col] = ""
        
        # Reordenar para asegurar coincidencia exacta con el esquema
        dfs[clave] = dfs[clave][columnas]
    except Exception as e:
        dfs[clave] = pd.DataFrame(columns=columnas)

# --- MENÚ DE NAVEGACIÓN PRINCIPAL ---
st.sidebar.markdown("### 🚀 Operaciones")
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
    df_f = dfs['finanzas'].copy()
    
    if not df_f.empty:
        df_f['Fecha'] = pd.to_datetime(df_f['Fecha'], errors='coerce')
        df_f['Monto ($)'] = pd.to_numeric(df_f['Monto ($)'], errors='coerce').fillna(0.0)
        
        filtro_tiempo = st.selectbox("📅 Vista Temporal del Balance:", [
            "Total Histórico", 
            "Anual (Año Actual)", 
            "Mensual (Mes Actual)", 
            "Semanal (Últimos 7 días)",
            "Rango de Fechas Personalizado"
        ])
        
        fecha_actual = datetime.now()
        df_filtrado = df_f.copy()
        
        if filtro_tiempo == "Anual (Año Actual)":
            df_filtrado = df_f[df_f['Fecha'].dt.year == fecha_actual.year]
        elif filtro_tiempo == "Mensual (Mes Actual)":
            df_filtrado = df_f[(df_f['Fecha'].dt.year == fecha_actual.year) & (df_f['Fecha'].dt.month == fecha_actual.month)]
        elif filtro_tiempo == "Semanal (Últimos 7 días)":
            df_filtrado = df_f[(fecha_actual - df_f['Fecha']).dt.days <= 7]
        elif filtro_tiempo == "Rango de Fechas Personalizado":
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                f_inicio = st.date_input("Fecha Inicio:", datetime(fecha_actual.year, 1, 1))
            with col_p2:
                f_fin = st.date_input("Fecha Fin:", fecha_actual)
            
            t_inicio = pd.to_datetime(f_inicio)
            t_fin = pd.to_datetime(f_fin).replace(hour=23, minute=59, second=59)
            df_filtrado = df_f[(df_f['Fecha'] >= t_inicio) & (df_f['Fecha'] <= t_fin)]

        ingresos = df_filtrado[(df_filtrado['Tipo'] == 'Ingreso') & (df_filtrado['Estado Deuda'] == 'Liquidado')]['Monto ($)'].sum()
        gastos = df_filtrado[(df_filtrado['Tipo'] == 'Gasto') & (df_filtrado['Estado Deuda'] == 'Liquidado')]['Monto ($)'].sum()
        
        por_cobrar = df_filtrado[(df_filtrado['Tipo'] == 'Ingreso') & (df_filtrado['Estado Deuda'] == 'Por Cobrar')]['Monto ($)'].sum()
        por_pagar = df_filtrado[(df_filtrado['Tipo'] == 'Gasto') & (df_filtrado['Estado Deuda'] == 'Por Pagar')]['Monto ($)'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("🟢 Ingresos Efectivos", f"${ingresos:,.2f}")
        col2.metric("🔴 Gastos Efectivos", f"${gastos:,.2f}")
        col3.metric("💰 Utilidad Real", f"${ingresos - gastos:,.2f}")
        
        st.markdown("### ⚠️ Control de Cuentas y Deudas (Período Seleccionado)")
        cold1, cold2 = st.columns(2)
        cold1.metric("📥 Total por Cobrar (Clientes)", f"${por_cobrar:,.2f}")
        cold2.metric("📤 Total por Pagar (Proveedores)", f"${por_pagar:,.2f}")
        
        st.markdown("---")
        st.markdown("### 🖨️ Generación y Descarga de Reportes Financieros")
        
        df_reporte = df_filtrado.copy()
        if not df_reporte.empty:
            df_reporte['Fecha'] = df_reporte['Fecha'].dt.strftime('%Y-%m-%d')
            
        csv_data = df_reporte.sort_values(by='Fecha', ascending=False).to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Descargar Reporte Desglosado Actual (Excel / CSV)",
            data=csv_data,
            file_name=f"Reporte_Financiero_RanchoAE_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

        st.markdown("---")
        t1, t2, t3 = st.tabs(["📋 Libro de Movimientos y Edición", "📊 Gráficas de Rendimiento", "🔍 Análisis por Lote"])
        
        with t1:
            st.subheader("Historial y Modificación de Transacciones")
            sub_tab_vista, sub_tab_editar = st.tabs(["🔍 Ver Tabla de Datos", "⚙️ Corregir o Eliminar Registro"])
            
            with sub_tab_vista:
                df_mostrar = df_filtrado.copy()
                if not df_mostrar.empty:
                    df_mostrar['Fecha'] = df_mostrar['Fecha'].dt.strftime('%Y-%m-%d')
                st.dataframe(df_mostrar.sort_values(by='Fecha', ascending=False), use_container_width=True)
                
            with sub_tab_editar:
                st.markdown("#### ⚙️ Panel de Corrección de Datos")
                if not dfs['finanzas'].empty:
                    id_editar = st.selectbox("Selecciona el ID del movimiento que deseas corregir o borrar:", dfs['finanzas']['ID'].tolist(), key="sb_id_editar")
                    
                    datos_mov = dfs['finanzas'][dfs['finanzas']['ID'] == id_editar].iloc[0]
                    
                    # Validación segura de conversión numérica para evitar caídas catastróficas
                    try:
                        monto_defecto = float(datos_mov['Monto ($)']) if pd.notnull(datos_mov['Monto ($)']) else 0.0
                    except:
                        monto_defecto = 0.0

                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        edit_concepto = st.text_input("Concepto / Detalle:", value=str(datos_mov['Concepto']), key="ti_edit_concepto")
                        edit_monto = st.number_input("Monto ($):", value=monto_defecto, min_value=0.0, key="ni_edit_monto")
                        edit_cat = st.text_input("Categoría:", value=str(datos_mov['Categoría']), key="ti_edit_cat")
                    with col_ed2:
                        estado_actual = datos_mov['Estado Deuda']
                        opciones_estado = ["Liquidado", "Por Cobrar", "Por Pagar"]
                        index_estado = opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0
                        edit_estado = st.selectbox("Estado del Pago:", opciones_estado, index=index_estado, key="sb_edit_estado")
                        
                        lista_lotes_ed = ["Ninguno / Administración General"] + dfs['lotes']['Nombre del Lote'].tolist()
                        index_lote = lista_lotes_ed.index(datos_mov['Lote Asociado']) if datos_mov['Lote Asociado'] in lista_lotes_ed else 0
                        edit_lote = st.selectbox("Lote Asociado:", lista_lotes_ed, index=index_lote, key="sb_edit_lote")
                        
                        opciones_metodo = ["Efectivo", "Tarjeta de Crédito/Débito", "Transferencia Bancaria", "Otro"]
                        index_metodo = opciones_metodo.index(datos_mov['Método Pago']) if datos_mov['Método Pago'] in opciones_metodo else 0
                        edit_metodo = st.selectbox("Método Pago:", opciones_metodo, index=index_metodo, key="sb_edit_metodo")
                    
                    col_b_acts = st.columns(2)
                    with col_b_acts[0]:
                        if st.button("💾 Guardar Corrección Manual", key="btn_save_manual"):
                            df_original = dfs['finanzas'].copy()
                            df_original.loc[df_original['ID'] == id_editar, 'Concepto'] = edit_concepto
                            df_original.loc[df_original['ID'] == id_editar, 'Monto ($)'] = edit_monto
                            df_original.loc[df_original['ID'] == id_editar, 'Categoría'] = edit_cat
                            df_original.loc[df_original['ID'] == id_editar, 'Estado Deuda'] = edit_estado
                            df_original.loc[df_original['ID'] == id_editar, 'Lote Asociado'] = edit_lote
                            df_original.loc[df_original['ID'] == id_editar, 'Método Pago'] = edit_metodo
                            
                            conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['finanzas'], data=df_original)
                            st.success(f"¡El movimiento con ID {id_editar} ha sido corregido con éxito!")
                            st.rerun()
                    with col_b_acts[1]:
                        if st.button("❌ Eliminar Registro Definitivamente", key="btn_delete_manual"):
                            df_original = dfs['finanzas'].copy()
                            df_original = df_original[df_original['ID'] != id_editar]
                            
                            conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['finanzas'], data=df_original)
                            st.warning(f"Movimiento con ID {id_editar} eliminado.")
                            st.rerun()
                else:
                    st.info("No hay datos disponibles en la base central para editar.")
            
        with t2:
            if not df_filtrado.empty:
                st.subheader("Distribución Financiera del Período")
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
            lote_sel = st.selectbox("Selecciona un lote para analizar:", lotes_existentes, key="sb_analisis_lote")
            if lote_sel != "Todos":
                df_lote = df_f[df_f['Lote Asociado'] == lote_sel]
                if not df_lote.empty:
                    df_lote['Fecha'] = df_lote['Fecha'].dt.strftime('%Y-%m-%d')
                    st.dataframe(df_lote, use_container_width=True)
                    il = df_lote[df_lote['Tipo'] == 'Ingreso']['Monto ($)'].sum()
                    gl = df_lote[df_lote['Tipo'] == 'Gasto']['Monto ($)'].sum()
                    st.info(f"Ganancia Neta del Lote {lote_sel}: ${il - gl:,.2f}")
                else:
                    st.info(f"No hay registros financieros vinculados al lote: {lote_sel}")
    else:
        st.info("No hay datos financieros registrados aún.")

# ==========================================
# 2. REGISTRO DE MOVIMIENTOS
# ==========================================
elif opcion_menu == "💰 Registro de Movimientos y Deudas":
    st.header("💰 Registrar Nueva Operación Financiera")
    
    tipo_m = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"], key="sb_reg_tipo")
    
    if tipo_m == "Ingreso":
        cat_base = ["Liquidación / Venta de Ganado", "Cobro de Fletes / Logística", "Venta de Forraje", "OTRA (Agregar de forma manual)"]
    else:
        cat_base = ["Alimentación (Sorgo, bagazo de caña, pollinaza)", "Combustible (Diésel)", "Mantenimiento", "Salud Animal", "Nóminas", "OTRA (Agregar de forma manual)"]
        
    cat_sel = st.selectbox("Categoría de la Operación", cat_base, key="sb_reg_cat")
    
    categoria_final = cat_sel
    if cat_sel == "OTRA (Agregar de forma manual)":
        categoria_final = st.text_input("Escribe la nueva categoría manual:", key="ti_reg_cat_manual")

    with st.form("form_finanzas", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_c = st.date_input("Fecha de Operación", datetime.now())
            concepto_c = st.text_input("Detalle / Concepto")
            monto_c = st.number_input("Monto ($)", min_value=0.0, step=100.0)

        with col_f2:
            metodo_p = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta de Crédito/Débito", "Transferencia Bancaria", "Otro"])
            lista_lotes = ["Ninguno / Administración General"] + dfs['lotes']['Nombre del Lote'].tolist()
            lote_asoc = st.selectbox("Asociar este movimiento al Lote:", lista_lotes)
            
        st.markdown("---")
        st.markdown("#### 2. Configuración de Créditos / Deudas")
        estado_d = st.selectbox("Estado del pago:", ["Liquidado", "Por Cobrar" if tipo_m == "Ingreso" else "Por Pagar"])
        fecha_venc = st.date_input("Fecha límite de cobro/pago (Si es deuda)", datetime.now())
        
        btn_guardar_f = st.form_submit_button("💾 Guardar Registro Contable")
        
    if btn_guardar_f:
        if categoria_final.strip() == "":
            st.error("Por favor, especifica una categoría válida.")
        else:
            df_f = dfs['finanzas'].copy()
            
            if not df_f.empty:
                ids_numericos = pd.to_numeric(df_f['ID'], errors='coerce').fillna(999)
                nuevo_id = int(ids_numericos.max() + 1)
            else:
                nuevo_id = 1000

            nueva_fila = pd.DataFrame([[
                nuevo_id, fecha_c.strftime('%Y-%m-%d'), tipo_m, categoria_final, concepto_c, monto_c, metodo_p, lote_asoc, estado_d, fecha_venc.strftime('%Y-%m-%d')
            ]], columns=COL_FINANZAS)
            
            df_f = pd.concat([df_f, nueva_fila], ignore_index=True)
            
            conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['finanzas'], data=df_f)
            st.success("¡Movimiento contable guardado exitosamente!")
            st.rerun()

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
            df_l = dfs['lotes'].copy()
            nueva_fila = pd.DataFrame([[nombre_lote, desc_lote, datetime.now().strftime('%Y-%m-%d')]], columns=COL_LOTES)
            df_l = pd.concat([df_l, nueva_fila], ignore_index=True)
            
            conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['lotes'], data=df_l)
            st.success(f"Lote '{nombre_lote}' creado con éxito.")
            st.rerun()
            
    with col_l2:
        st.subheader("📋 Lotes Activos")
        if not dfs['lotes'].empty:
            st.dataframe(dfs['lotes'], use_container_width=True)
            
            st.markdown("#### ❌ Quitar Lote")
            lote_a_borrar = st.selectbox("Selecciona un lote para dar de baja:", dfs['lotes']['Nombre del Lote'].tolist(), key="sb_lote_borrar")
            if st.button("Eliminar Lote definitivamente", key="btn_lote_borrar"):
                df_l = dfs['lotes'].copy()
                df_l = df_l[df_l['Nombre del Lote'] != lote_a_borrar]
                
                conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['lotes'], data=df_l)
                st.warning(f"Lote '{lote_a_borrar}' eliminado.")
                st.rerun()
        else:
            st.info("No hay lotes registrados todavía.")

# ==========================================
# 4. GESTIÓN DE EMPLEADOS
# ==========================================
elif opcion_menu == "🤠 Gestión de Empleados":
    st.header("🤠 Personal y Miembros de la Empresa")
    
    tab_reg, tab_edit = st.tabs(["➕ Registrar / Ver Lista", "⚙️ Editar o Eliminar Manualmente"])
    
    with tab_reg:
        col_e1, col_e2 = st.columns([1, 2])
        with col_e1:
            st.subheader("Registrar Empleado")
            with st.form("form_emp", clear_on_submit=True):
                nom_emp = st.text_input("Nombre Completo")
                tel_emp = st.text_input("Número de Teléfono")
                puesto_emp = st.selectbox("Función / Puesto Asignado:", ["Chofer de Camión/Logística", "Caporal / Vaquero", "Administrador", "Encargado de Alimentos", "Otro"])
                btn_emp = st.form_submit_button("Registrar Empleado")
                
            if btn_emp and nom_emp.strip() != "":
                df_e = dfs['empleados'].copy()
                nueva_fila = pd.DataFrame([[nom_emp, tel_emp, puesto_emp, datetime.now().strftime('%Y-%m-%d')]], columns=COL_EMPLEADOS)
                df_e = pd.concat([df_e, nueva_fila], ignore_index=True)
                
                conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['empleados'], data=df_e)
                st.success("Empleado registrado correctamente.")
                st.rerun()
                
        with col_e2:
            st.subheader("📋 Plantilla de Trabajo Actual")
            if not dfs['empleados'].empty:
                st.dataframe(dfs['empleados'], use_container_width=True)
            else:
                st.info("Aún no tienes empleados registrados.")

    with tab_edit:
        st.subheader("⚙️ Modificar o Dar de Baja Personal")
        if not dfs['empleados'].empty:
            df_e = dfs['empleados'].copy()
            emp_seleccionado = st.selectbox("Selecciona el empleado que deseas modificar o eliminar:", df_e['Nombre'].tolist(), key="sb_emp_edit")
            datos_emp = df_e[df_e['Nombre'] == emp_seleccionado].iloc[0]
            
            col_ed1, col_ed2 = st.columns(2)
            with col_ed1:
                nuevo_tel = st.text_input("Modificar Teléfono:", value=str(datos_emp['Teléfono']), key="ti_emp_tel")
            with col_ed2:
                puestos_lista = ["Chofer de Camión/Logística", "Caporal / Vaquero", "Administrador", "Encargado de Alimentos", "Otro"]
                index_puesto = puestos_lista.index(datos_emp['Puesto / Función']) if datos_emp['Puesto / Función'] in puestos_lista else 0
                nuevo_puesto = st.selectbox("Modificar Puesto:", puestos_lista, index=index_puesto, key="sb_emp_puesto")
            
            col_actions = st.columns(2)
            with col_actions[0]:
                if st.button("💾 Guardar Cambios del Empleado", key="btn_emp_save"):
                    df_e.loc[df_e['Nombre'] == emp_seleccionado, 'Teléfono'] = nuevo_tel
                    df_e.loc[df_e['Nombre'] == emp_seleccionado, 'Puesto / Función'] = nuevo_puesto
                    
                    conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['empleados'], data=df_e)
                    st.success(f"Datos de {emp_seleccionado} actualizados.")
                    st.rerun()
            with col_actions[1]:
                if st.button("❌ Eliminar Empleado de la Empresa", key="btn_emp_delete"):
                    df_e = df_e[df_e['Nombre'] != emp_seleccionado]
                    
                    conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['empleados'], data=df_e)
                    st.warning(f"{emp_seleccionado} ha sido removido del registro.")
                    st.rerun()
        else:
            st.info("No hay empleados para modificar.")

# ==========================================
# 5. CLIENTES Y VENTAS
# ==========================================
elif opcion_menu == "🤝 Clientes y Ventas":
    st.header("🤝 Registro de Clientes Comerciales")
    
    tab_cli_ver, tab_cli_edit = st.tabs(["➕ Registrar / Ver Lista", "⚙️ Editar o Eliminar Manualmente"])
    
    with tab_cli_ver:
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            st.subheader("Registrar Cliente")
            with st.form("form_cli", clear_on_submit=True):
                nom_cli = st.text_input("Nombre o Razón Social")
                cont_cli = st.text_input("Persona de Contacto")
                tel_cli = st.text_input("Teléfono de Contacto")
                notas_cli = st.text_input("¿Qué le vendemos? / Notas")
                btn_cli = st.form_submit_button("Guardar Cliente")
                
            if btn_cli and nom_cli.strip() != "":
                df_c = dfs['clientes'].copy()
                nueva_fila = pd.DataFrame([[nom_cli, cont_cli, tel_cli, notas_cli]], columns=COL_CLIENTES)
                df_c = pd.concat([df_c, nueva_fila], ignore_index=True)
                
                conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['clientes'], data=df_c)
                st.success("Cliente guardado en catálogo.")
                st.rerun()
                
        with col_c2:
            st.subheader("📋 Directorio de Clientes")
            if not dfs['clientes'].empty:
                st.dataframe(dfs['clientes'], use_container_width=True)
            else:
                st.info("No hay clientes registrados.")

    with tab_cli_edit:
        st.subheader("⚙️ Modificar o Dar de Baja Clientes")
        if not dfs['clientes'].empty:
            df_c = dfs['clientes'].copy()
            cli_seleccionado = st.selectbox("Selecciona el cliente a editar/eliminar:", df_c['Nombre / Razón Social'].tolist(), key="sb_cli_edit")
            datos_cli = df_c[df_c['Nombre / Razón Social'] == cli_seleccionado].iloc[0]
            
            col_ced1, col_ced2, col_ced3 = st.columns(3)
            with col_ced1:
                nuevo_cont_cli = st.text_input("Contacto:", value=str(datos_cli['Contacto']), key="ti_cli_cont")
            with col_ced2:
                nuevo_tel_cli = st.text_input("Teléfono:", value=str(datos_cli['Teléfono']), key="ti_cli_tel")
            with col_ced3:
                nuevas_notas_cli = st.text_input("Notas comerciales:", value=str(datos_cli['Notas']), key="ti_cli_notas")
                
            col_c_acts = st.columns(2)
            with col_c_acts[0]:
                if st.button("💾 Guardar Cambios del Cliente", key="btn_cli_save"):
                    df_c.loc[df_c['Nombre / Razón Social'] == cli_seleccionado, 'Contacto'] = nuevo_cont_cli
                    df_c.loc[df_c['Nombre / Razón Social'] == cli_seleccionado, 'Teléfono'] = nuevo_tel_cli
                    df_c.loc[df_c['Nombre / Razón Social'] == cli_seleccionado, 'Notas'] = nuevas_notas_cli
                    
                    conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['clientes'], data=df_c)
                    st.success(f"Cliente '{cli_seleccionado}' actualizado.")
                    st.rerun()
            with col_c_acts[1]:
                if st.button("❌ Eliminar Cliente del Catálogo", key="btn_cli_delete"):
                    df_c = df_c[df_c['Nombre / Razón Social'] != cli_seleccionado]
                    
                    conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['clientes'], data=df_c)
                    st.warning(f"Cliente '{cli_seleccionado}' removido.")
                    st.rerun()
        else:
            st.info("No hay clientes para modificar.")

# ==========================================
# 6. PROVEEDORES E INSUMOS
# ==========================================
elif opcion_menu == "🚜 Proveedores e Insumos":
    st.header("🚜 Directorio de Proveedores")
    
    tab_prov_ver, tab_prov_edit = st.tabs(["➕ Registrar / Ver Lista", "⚙️ Editar o Eliminar Manualmente"])
    
    with tab_prov_ver:
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            st.subheader("Registrar Proveedor")
            with st.form("form_prov", clear_on_submit=True):
                nom_prov = st.text_input("Nombre de la Empresa / Proveedor")
                cont_prov = st.text_input("Atendido por")
                tel_prov = st.text_input("Teléfono")
                ins_prov = st.selectbox("Insumo Principal que provee:", ["Alimento / Granos", "Diésel / Combustible", "Fierro / Refacciones", "Medicinas / Veterinaria", "Otros"])
                btn_prov = st.form_submit_button("Guardar Proveedor")
                
            if btn_prov and nom_prov.strip() != "":
                df_p = dfs['proveedores'].copy()
                nueva_fila = pd.DataFrame([[nom_prov, cont_prov, tel_prov, ins_prov]], columns=COL_PROVEEDORES)
                df_p = pd.concat([df_p, nueva_fila], ignore_index=True)
                
                conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['proveedores'], data=df_p)
                st.success("Proveedor registrado exitosamente.")
                st.rerun()
                
        with col_p2:
            st.subheader("📋 Lista de Proveedores Autorizados")
            if not dfs['proveedores'].empty:
                st.dataframe(dfs['proveedores'], use_container_width=True)
            else:
                st.info("No hay proveedores en la lista.")

    with tab_prov_edit:
        st.subheader("⚙️ Modificar o Dar de Baja Proveedores")
        if not dfs['proveedores'].empty:
            df_p = dfs['proveedores'].copy()
            prov_seleccionado = st.selectbox("Selecciona el proveedor a editar/eliminar:", df_p['Nombre Proveedor'].tolist(), key="sb_prov_edit")
            datos_prov = df_p[df_p['Nombre Proveedor'] == prov_seleccionado].iloc[0]
            
            col_ped1, col_ped2, col_ped3 = st.columns(3)
            with col_ped1:
                nuevo_cont_prov = st.text_input("Atendido por:", value=str(datos_prov['Contacto']), key="ti_prov_cont")
            with col_ped2:
                nuevo_tel_prov = st.text_input("Teléfono:", value=str(datos_prov['Teléfono']), key="ti_prov_tel")
            with col_ped3:
                insumos_lista = ["Alimento / Granos", "Diésel / Combustible", "Fierro / Refacciones", "Medicinas / Veterinaria", "Otros"]
                index_insumo = insumos_lista.index(datos_prov['Insumo Principal']) if datos_prov['Insumo Principal'] in insumos_lista else 0
                nuevo_ins_prov = st.selectbox("Modificar Insumo:", insumos_lista, index=index_insumo, key="sb_prov_insumo")
                
            col_p_acts = st.columns(2)
            with col_p_acts[0]:
                if st.button("💾 Guardar Cambios del Proveedor", key="btn_prov_save"):
                    df_p.loc[df_p['Nombre Proveedor'] == prov_seleccionado, 'Contacto'] = nuevo_cont_prov
                    df_p.loc[df_p['Nombre Proveedor'] == prov_seleccionado, 'Teléfono'] = nuevo_tel_prov
                    df_p.loc[df_p['Nombre Proveedor'] == prov_seleccionado, 'Insumo Principal'] = nuevo_ins_prov
                    
                    conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['proveedores'], data=df_p)
                    st.success(f"Proveedor '{prov_seleccionado}' actualizado.")
                    st.rerun()
            with col_p_acts[1]:
                if st.button("❌ Eliminar Proveedor del Directorio", key="btn_prov_delete"):
                    df_p = df_p[df_p['Nombre Proveedor'] != prov_seleccionado]
                    
                    conn.update(spreadsheet=URL_HOJA_CENTRAL, worksheet=PESTANAS['proveedores'], data=df_p)
                    st.warning(f"Proveedor '{prov_seleccionado}' removido.")
                    st.rerun()
        else:
            st.info("No hay proveedores para modificar.")
