import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la plataforma
st.set_page_config(page_title="Administración de Rancho", layout="wide", page_icon="📈")
st.title(";💼 Panel de Administración Financiera")
st.markdown("### Control de Flujo de Efectivo, Insumos y Logística")

# Base de datos administrativa
ARCHIVO_ADMIN = 'administracion_rancho.csv';
columnas_admin = ['Fecha', 'Tipo', 'Categoría', 'Concepto / Detalle', 'Monto ($)']

if os.path.exists(ARCHIVO_ADMIN):
df_admin = pd.read_csv(ARCHIVO_ADMIN)
else:
df_admin = pd.DataFrame(columns=columnas_admin)

# --- PANEL LATERAL: CAPTURA DE MOVIMIENTOS ---
st.sidebar.header(";📥 Registro Administrativo")

with st.sidebar.form("formulario_admin";, clear_on_submit=True):
fecha = st.date_input("Fecha Contable", datetime.now())
tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"])

# Categorías puramente administrativas del rancho y transporte
if tipo == "Ingreso":
categoria = st.selectbox("Origen del Ingreso", [
"Liquidación / Venta de Ganado",
"Cobro de Fletes / Logística",
"Venta de Subproductos / Forraje",
"Otros Ingresos"
])
else:
categoria = st.selectbox("Destino del Gasto", [
"Alimentación y Nutrición (Sorgo, pollinaza, bagazo)",
"Combustibles y Peajes (Diésel, casetas)",
"Mantenimiento de Activos (Camión, tractor, corrales)",
"Salud Animal (Vacunas, desparasitantes, veterinario)",
"Nóminas y Rayas (Personal de campo y choferes)",
"Gastos Legales y Facturación",
"Administración General"
])

concepto = st.text_input("Concepto Detallado", placeholder="Ej. Compra de 5 tons de sorgo, Flete viaje a...")
monto = st.number_input("Monto en Pesos ($)", min_value=0.0, step=100.0, format="%.2f")

boton_guardar = st.form_submit_button("Registrar en Libros")

# Guardar datos
if boton_guardar:
if concepto.strip() == "" or monto == 0:
st.sidebar.error(";❌ Error: El concepto y el monto no pueden estar vacíos.")
else:
nueva_fila = pd.DataFrame([[fecha.strftime('%Y-%m-%d';), tipo, categoria, concepto, monto]], columns=columnas_admin)
df_admin = pd.concat([df_admin, nueva_fila], ignore_index=True)
df_admin.to_csv(ARCHIVO_ADMIN, index=False)
st.sidebar.success(";✅ Registro contable guardado.")
st.rerun()

# --- CUERPO PRINCIPAL: BALANCE Y ANÁLISIS ---
if not df_admin.empty:
ingresos = df_admin[df_admin['Tipo'] == 'Ingreso']['Monto ($)'].sum()
gastos = df_admin[df_admin['Tipo'] == 'Gasto']['Monto ($)'].sum()
utilidad_neta = ingresos - gastos
else:
ingresos, gastos, utilidad_neta = 0.0, 0.0, 0.0

# Indicadores Financieros
col1, col2, col3 = st.columns(3)
col1.metric(";📈 Ingresos Brutos", f"${ingresos:,.2f}")
col2.metric(";📉 Gastos Operativos", f"${gastos:,.2f}")
# El delta cambia a rojo si la utilidad baja, o verde si es positiva
col3.metric(";💰 Utilidad / Margen Neto", f"${utilidad_neta:,.2f}", delta=f"${utilidad_neta:,.2f}")

st.markdown("---";)

# --- REPORTES DE CONTROL ---
if not df_admin.empty:
tab1, tab2 = st.tabs(["📋 Libro de Diario (Historial)", "📊 Análisis de Gastos e Ingresos"])

with tab1:
st.subheader("Historial General de Movimientos")
# Filtros administrativos rápidos
col_f1, col_f2 = st.columns(2)
with col_f1:
filtro_tipo = st.multiselect("Filtrar por Tipo:", ["Ingreso", "Gasto"], default=["Ingreso", "Gasto"])
with col_f2:
filtro_cat = st.selectbox("Filtrar por Categoría Específica:", ["Todas"] + list(df_admin['Categoría'].unique()))

# Aplicar los filtros seleccionados
df_filtrado = df_admin[df_admin['Tipo'].isin(filtro_tipo)]
if filtro_cat != "Todas":
df_filtrado = df_filtrado[df_filtrado['Categoría'] == filtro_cat]

st.dataframe(df_filtrado.sort_index(ascending=False), use_container_width=True)

with tab2:
st.subheader(";¿A dónde se está yendo el dinero?")

col_g1, col_g2 = st.columns(2)

with col_g1:
st.markdown("**Gastos por Categoría Operativa:**")
df_gastos = df_admin[df_admin['Tipo'] == 'Gasto']
if not df_gastos.empty:
gastos_cat = df_gastos.groupby('Categoría')['Monto ($)'].sum()
st.bar_chart(gastos_cat)
else:
st.info("No hay gastos registrados todavía.")

with col_g2:
st.markdown("**Fuentes de Ingreso:**")
df_ingresos = df_admin[df_admin['Tipo'] == 'Ingreso']
if not df_ingresos.empty:
ingresos_cat = df_ingresos.groupby('Categoría')['Monto ($)'].sum()
st.bar_chart(ingresos_cat)
else:
st.info("No hay ingresos registrados todavía.")
else:
st.info("El sistema administrativo está limpio y listo para recibir datos. Registra un movimiento a la izquierda para comenzar.")
import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la plataforma
st.set_page_config(page_title="Administración de Rancho", layout="wide", page_icon="📈")
st.title(";💼 Panel de Administración Financiera")
st.markdown("### Control de Flujo de Efectivo, Insumos y Logística")

# Base de datos administrativa
ARCHIVO_ADMIN = 'administracion_rancho.csv';
columnas_admin = ['Fecha', 'Tipo', 'Categoría', 'Concepto / Detalle', 'Monto ($)']

if os.path.exists(ARCHIVO_ADMIN):
df_admin = pd.read_csv(ARCHIVO_ADMIN)
else:
df_admin = pd.DataFrame(columns=columnas_admin)

# --- PANEL LATERAL: CAPTURA DE MOVIMIENTOS ---
st.sidebar.header(";📥 Registro Administrativo")

with st.sidebar.form("formulario_admin";, clear_on_submit=True):
fecha = st.date_input("Fecha Contable", datetime.now())
tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"])

# Categorías puramente administrativas del rancho y transporte
if tipo == "Ingreso":
categoria = st.selectbox("Origen del Ingreso", [
"Liquidación / Venta de Ganado",
"Cobro de Fletes / Logística",
"Venta de Subproductos / Forraje",
"Otros Ingresos"
])
else:
categoria = st.selectbox("Destino del Gasto", [
"Alimentación y Nutrición (Sorgo, pollinaza, bagazo)",
"Combustibles y Peajes (Diésel, casetas)",
"Mantenimiento de Activos (Camión, tractor, corrales)",
"Salud Animal (Vacunas, desparasitantes, veterinario)",
"Nóminas y Rayas (Personal de campo y choferes)",
"Gastos Legales y Facturación",
"Administración General"
])

concepto = st.text_input("Concepto Detallado", placeholder="Ej. Compra de 5 tons de sorgo, Flete viaje a...")
monto = st.number_input("Monto en Pesos ($)", min_value=0.0, step=100.0, format="%.2f")

boton_guardar = st.form_submit_button("Registrar en Libros")

# Guardar datos
if boton_guardar:
if concepto.strip() == "" or monto == 0:
st.sidebar.error(";❌ Error: El concepto y el monto no pueden estar vacíos.")
else:
nueva_fila = pd.DataFrame([[fecha.strftime('%Y-%m-%d';), tipo, categoria, concepto, monto]], columns=columnas_admin)
df_admin = pd.concat([df_admin, nueva_fila], ignore_index=True)
df_admin.to_csv(ARCHIVO_ADMIN, index=False)
st.sidebar.success(";✅ Registro contable guardado.")
st.rerun()

# --- CUERPO PRINCIPAL: BALANCE Y ANÁLISIS ---
if not df_admin.empty:
ingresos = df_admin[df_admin['Tipo'] == 'Ingreso']['Monto ($)'].sum()
gastos = df_admin[df_admin['Tipo'] == 'Gasto']['Monto ($)'].sum()
utilidad_neta = ingresos - gastos
else:
ingresos, gastos, utilidad_neta = 0.0, 0.0, 0.0

# Indicadores Financieros
col1, col2, col3 = st.columns(3)
col1.metric(";📈 Ingresos Brutos", f"${ingresos:,.2f}")
col2.metric(";📉 Gastos Operativos", f"${gastos:,.2f}")
# El delta cambia a rojo si la utilidad baja, o verde si es positiva
col3.metric(";💰 Utilidad / Margen Neto", f"${utilidad_neta:,.2f}", delta=f"${utilidad_neta:,.2f}")

st.markdown("---";)

# --- REPORTES DE CONTROL ---
if not df_admin.empty:
tab1, tab2 = st.tabs(["📋 Libro de Diario (Historial)", "📊 Análisis de Gastos e Ingresos"])

with tab1:
st.subheader("Historial General de Movimientos")
# Filtros administrativos rápidos
col_f1, col_f2 = st.columns(2)
with col_f1:
filtro_tipo = st.multiselect("Filtrar por Tipo:", ["Ingreso", "Gasto"], default=["Ingreso", "Gasto"])
with col_f2:
filtro_cat = st.selectbox("Filtrar por Categoría Específica:", ["Todas"] + list(df_admin['Categoría'].unique()))

# Aplicar los filtros seleccionados
df_filtrado = df_admin[df_admin['Tipo'].isin(filtro_tipo)]
if filtro_cat != "Todas":
df_filtrado = df_filtrado[df_filtrado['Categoría'] == filtro_cat]

st.dataframe(df_filtrado.sort_index(ascending=False), use_container_width=True)

with tab2:
st.subheader(";¿A dónde se está yendo el dinero?")

col_g1, col_g2 = st.columns(2)

with col_g1:
st.markdown("**Gastos por Categoría Operativa:**")
df_gastos = df_admin[df_admin['Tipo'] == 'Gasto']
if not df_gastos.empty:
gastos_cat = df_gastos.groupby('Categoría')['Monto ($)'].sum()
st.bar_chart(gastos_cat)
else:
st.info("No hay gastos registrados todavía.")

with col_g2:
st.markdown("**Fuentes de Ingreso:**")
df_ingresos = df_admin[df_admin['Tipo'] == 'Ingreso']
if not df_ingresos.empty:
ingresos