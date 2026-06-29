import streamlit as st
import pandas as pd
from datetime import datetime
import os

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

# Cargar o inicializar archivos de forma segura
dfs = {}
for clave, archivo in ARCHIVOS.items():
    columnas = locals()[f"COL_{clave.upper()}"]
    if os.path.exists(archivo):
        try:
            dfs[clave] = pd.read_csv(archivo)
            # Asegurar que tengan las columnas correctas si el archivo venía vacío o incompleto
            for col in columnas:
                if col not in dfs[clave].columns:
                    dfs[clave][col] = ""
        except:
            dfs[clave] = pd.DataFrame(columns=columnas)
    else:
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
    df_f = dfs['finanzas']
    
    if not df_f.empty:
        df_f['Fecha'] = pd.to_datetime(df_f['Fecha'])
        df_f['Monto ($)'] = pd.to_numeric(df_f['Monto ($)'])
        
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

        ingresos = df_filtrado[(df_filtrado['Tipo'] == 'Ingreso') & (df_filtrado['Estado Deuda'] == 'Liquidado')]['Monto ($)'].sum()
        gastos = df_filtrado[(df_filtrado['Tipo'] == 'Gasto') & (df_filtrado['Estado Deuda'] == 'Liquidado')]['Monto ($)'].sum()
        
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
        
        t1, t2, t3 = st.tabs(["📋 Libro de Movimientos", "📊 Gráficas de Rendimiento", "🔍 Análisis por Lote"])
        with t1:
            st.subheader("Historial de Transacciones Registradas")
            
            st.markdown("#### 🗑️ Eliminar un registro por error")
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
# 2. REGISTRO DE MOVIMIENTOS (Solución de Categorías)
# ==========================================
elif opcion_menu == "💰 Registro de Movimientos y Deudas":
    st.header("💰 Registrar Nueva Operación Financiera")
    
    # El tipo de movimiento se selecciona afuera del formulario para actualizar las categorías dinámicamente sin errores
    tipo_m = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"])
    
    if tipo_m == "Ingreso":
        cat_base = ["Liquidación / Venta de Ganado", "Cobro de Fletes / Logística", "Venta de Forraje", "OTRA (Agregar de forma manual)"]
    else:
        cat_base = ["Alimentación (Sorgo, pollinaza)", "Combustible (Diésel)", "Mantenimiento", "Salud Animal", "Nóminas", "OTRA (Agregar de forma manual)"]
        
    cat_sel = st.selectbox("Categoría de la Operación", cat_base)
    
    categoria_final = cat_sel
    if cat_sel == "OTRA (Agregar de forma manual)":
        categoria_final = st.text_input("Escribe la nueva categoría manual:")

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
        st.markdown("#### 📆 Configuración de Créditos / Deudas")
        estado_d = st.selectbox("Estado del pago:", ["Liquidado", "Por Cobrar" if tipo_m == "Ingreso" else "Por Pagar"])
        fecha_venc = st.date_input("Fecha límite de cobro/pago (Si es deuda)", datetime.now())
        
        btn_guardar_f = st.form_submit_button("💾 Guardar Registro Contable")
        
    if btn_guardar_f:
        if categoria_final.strip() == "":
            st.error("Por favor, especifica una categoría válida.")
        else:
            df_f = dfs['finanzas']
            nuevo_id = int(df_f['ID'].max() + 1) if not df_f.empty else 1000
            nueva_fila = pd.DataFrame([[
                nuevo_id, fecha_c.strftime('%Y-%m-%d'), tipo_m, categoria_final, concepto_c, monto_c, metodo_p, lote_asoc, estado_d, fecha_venc.strftime('%Y-%m-%d')
            ]], columns=COL_FINANZAS)
            
            df_f = pd.concat([df_f, nueva_fila], ignore_index=True)
            df_f.to_csv(ARCHIVOS['finanzas'], index=False)
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
# 4. GESTIÓN DE EMPLEADOS (Con Edición y Baja)
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
                df_e = dfs['empleados']
                nueva_fila = pd.DataFrame([[nom_emp, tel_emp, puesto_emp, datetime.now().strftime('%Y-%m-%d')]], columns=COL_EMPLEADOS)
                df_e = pd.concat([df_e, nueva_fila], ignore_index=True)
                df_e.to_csv(ARCHIVOS['empleados'], index=False)
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
            df_e = dfs['empleados']
            emp_seleccionado = st.selectbox("Selecciona el empleado que deseas modificar o eliminar:", df_e['Nombre'].tolist())
            
            # Obtener datos actuales del renglón elegido
            datos_emp = df_e[df_e['Nombre'] == emp_seleccionado].iloc[0]
            
            col_ed1, col_ed2 = st.columns(2)
            with col_ed1:
                nuevo_tel = st.text_input("Modificar Teléfono:", value=str(datos_emp['Teléfono']))
                nuevo_puesto = st.selectbox("Modificar Puesto:", ["Chofer de Camión/Logística", "Caporal / Vaquero", "Administrador", "Encargado de Alimentos", "Otro"], index=["Chofer de Camión/Logística", "Caporal / Vaquero", "Administrador", "Encargado de Alimentos", "Otro"].index(datos_emp['Puesto / Función']) if datos_emp['Puesto / Función'] in ["Chofer de Camión/Logística", "Caporal / Vaquero", "Administrador", "Encargado de Alimentos", "Otro"] else 0)
            
            col_actions = st.columns(2)
            with col_actions[0]:
                if st.button("💾 Guardar Cambios del Empleado"):
                    df_e.loc[df_e['Nombre'] == emp_seleccionado, 'Teléfono'] = nuevo_tel
                    df_e.loc[df_e['Nombre'] == emp_seleccionado, 'Puesto / Función'] = nuevo_puesto
                    df_e.to_csv(ARCHIVOS['empleados'], index=False)
                    st.success(f"Datos de {emp_seleccionado} actualizados.")
                    st.rerun()
            with col_actions[1]:
                if st.button("❌ Eliminar Empleado de la Empresa"):
                    df_e = df_e[df_e['Nombre'] != emp_seleccionado]
                    df_e.to_csv(ARCHIVOS['empleados'], index=False)
                    st.warning(f"{emp_seleccionado} ha sido removido del registro.")
                    st.rerun()
        else:
            st.info("No hay empleados para modificar.")

# ==========================================
# 5. CLIENTES Y VENTAS (Con Edición y Baja)
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

    with tab_cli_edit:
        st.subheader("⚙️ Modificar o Dar de Baja Clientes")
        if not dfs['clientes'].empty:
            df_c = dfs['clientes']
            cli_seleccionado = st.selectbox("Selecciona el cliente a editar/eliminar:", df_c['Nombre / Razón Social'].tolist())
            datos_cli = df_c[df_c['Nombre / Razón Social'] == cli_seleccionado].iloc[0]
            
            col_ced1, col_ced2 = st.columns(3)
            with col_ced1:
                nuevo_cont_cli = st.text_input("Contacto:", value=str(datos_cli['Contacto']))
            with col_ced2:
                nuevo_tel_cli = st.text_input("Teléfono:", value=str(datos_cli['Teléfono']))
            with col_ced2:
                nuevas_notas_cli = st.text_input("Notas comerciales:", value=str(datos_cli['Notas']))
                
            col_c_acts = st.columns(2)
            with col_c_acts[0]:
                if st.button("💾 Guardar Cambios del Cliente"):
                    df_c.loc[df_c['Nombre / Razón Social'] == cli_seleccionado, 'Contacto'] = nuevo_cont_cli
                    df_c.loc[df_c['Nombre / Razón Social'] == cli_seleccionado, 'Teléfono'] = nuevo_tel_cli
                    df_c.loc[df_c['Nombre / Razón Social'] == cli_seleccionado, 'Notas'] = nuevas_notas_cli
                    df_c.to_csv(ARCHIVOS['clientes'], index=False)
                    st.success(f"Cliente '{cli_seleccionado}' actualizado.")
                    st.rerun()
            with col_c_acts[1]:
                if st.button("❌ Eliminar Cliente del Catálogo"):
                    df_c = df_c[df_c['Nombre / Razón Social'] != cli_seleccionado]
                    df_c.to_csv(ARCHIVOS['clientes'], index=False)
                    st.warning(f"Cliente '{cli_seleccionado}' removido.")
                    st.rerun()
        else:
            st.info("No hay clientes para modificar.")

# ==========================================
# 6. PROVEEDORES E INSUMOS (Con Edición y Baja)
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

    with tab_prov_edit:
        st.subheader("⚙️ Modificar o Dar de Baja Proveedores")
        if not dfs['proveedores'].empty:
            df_p = dfs['proveedores']
            prov_seleccionado = st.selectbox("Selecciona el proveedor a editar/eliminar:", df_p['Nombre Proveedor'].tolist())
            datos_prov = df_p[df_p['Nombre Proveedor'] == prov_seleccionado].iloc[0]
            
            col_ped1, col_ped2 = st.columns(3)
            with col_ped1:
                nuevo_cont_prov = st.text_input("Atendido por:", value=str(datos_prov['Contacto']))
            with col_ped2:
                nuevo_tel_prov = st.text_input("Teléfono:", value=str(datos_prov['Teléfono']))
            with col_ped2:
                nuevo_ins_prov = st.selectbox("Modificar Insumo:", ["Alimento / Granos", "Diésel / Combustible", "Fierro / Refacciones", "Medicinas / Veterinaria", "Otros"], index=["Alimento / Granos", "Diésel / Combustible", "Fierro / Refacciones", "Medicinas / Veterinaria", "Otros"].index(datos_prov['Insumo Principal']) if datos_prov['Insumo Principal'] in ["Alimento / Granos", "Diésel / Combustible", "Fierro / Refacciones", "Medicinas / Veterinaria", "Otros"] else 0)
                
            col_p_acts = st.columns(2)
            with col_p_acts[0]:
                if st.button("💾 Guardar Cambios del Proveedor"):
                    df_p.loc[df_p['Nombre Proveedor'] == prov_seleccionado, 'Contacto'] = nuevo_cont_prov
                    df_p.loc[df_p['Nombre Proveedor'] == prov_seleccionado, 'Teléfono'] = nuevo_tel_prov
                    df_p.loc[df_p['Nombre Proveedor'] == prov_seleccionado, 'Insumo Principal'] = nuevo_ins_prov
                    df_p.to_csv(ARCHIVOS['proveedores'], index=False)
                    st.success(f"Proveedor '{prov_seleccionado}' actualizado.")
                    st.rerun()
            with col_p_acts[1]:
                if st.button("❌ Eliminar Proveedor del Directorio"):
                    df_p = df_p[df_p['Nombre Proveedor'] != prov_seleccionado]
                    df_p.to_csv(ARCHIVOS['proveedores'], index=False)
                    st.warning(f"Proveedor '{prov_seleccionado}' removido.")
                    st.rerun()
        else:
            st.info("No hay proveedores para modificar.")
