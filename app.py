import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA Y CONEXIÓN
# ---------------------------------------------------------
st.set_page_config(
    page_title="Rancho AE - Panel Financiero",
    page_icon="📊",
    layout="wide"
)

# Inicialización de la conexión a Supabase
# Modifica estos valores con tus credenciales reales o usa st.secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "TU_SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "TU_SUPABASE_ANON_KEY")

@st.cache_resource
def init_connection():
    if SUPABASE_URL == "TU_SUPABASE_URL" or SUPABASE_KEY == "TU_SUPABASE_ANON_KEY":
        st.warning("Por favor, configura correctamente tus credenciales de Supabase.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")

# ---------------------------------------------------------
# CARGA DE DATOS (CON CACHÉ OPTIMIZADA)
# ---------------------------------------------------------
@st.cache_data(ttl=60)  # Limpia la caché cada minuto automáticamente
def cargar_datos_finanzas():
    try:
        # Reemplaza 'finanzas' por el nombre exacto de tu tabla en Supabase
        respuesta = supabase.table("finanzas").select("*").execute()
        datos = respuesta.data
        
        if not datos:
            return pd.DataFrame(columns=['id', 'fecha', 'concepto', 'tipo', 'categoria', 'monto', 'nota'])
            
        df = pd.DataFrame(datos)
        
        # Conversión estricta de la columna de fecha
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['monto'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Error al extraer los datos: {e}")
        return pd.DataFrame()

# Carga inicial del DataFrame
df_finanzas = cargar_datos_finanzas()

# ---------------------------------------------------------
# INTERFAZ DE USUARIO: ENCABEZADO
# ---------------------------------------------------------
st.title("📊 Panel Financiero - Rancho AE")
st.markdown("Control de ingresos, egresos y balances históricos de la operación ganadera.")
st.write("---")

if df_finanzas.empty:
    st.info("No hay registros financieros disponibles en la base de datos o la tabla está vacía.")
else:
    # ---------------------------------------------------------
    # CONFIGURACIÓN Y FILTRO DE TIEMPO (SOLUCIONADO)
    # ---------------------------------------------------------
    st.subheader("📆 Filtro de Período Temporal")
    col_filtro, col_fechas = st.columns([2, 3])
    
    hoy = datetime.today()
    
    # Inicializamos por defecto cubriendo todo el día de hoy
    fecha_inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_fin = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)

    with col_filtro:
        periodo = st.selectbox(
            "Selecciona el período visualizado:",
            ["Todo el Historial", "Esta Semana", "Este Mes", "Este Año", "Rango Personalizado"]
        )

    with col_fechas:
        if periodo == "Esta Semana":
            lunes = hoy - timedelta(days=hoy.weekday())
            fecha_inicio = lunes.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = (lunes + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            st.info(f"Mostrando desde el lunes: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
            
        elif periodo == "Este Mes":
            fecha_inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = hoy.replace(day=28) + timedelta(days=4)
            ultimo_dia = next_month - timedelta(days=next_month.day)
            fecha_fin = ultimo_dia.replace(hour=23, minute=59, second=59, microsecond=999999)
            st.info(f"Mostrando el mes en curso: **{fecha_inicio.strftime('%B %Y')}**")
            
        elif periodo == "Este Año":
            fecha_inicio = hoy.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = hoy.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
            st.info(f"Mostrando el año en curso: **{hoy.year}**")
            
        elif periodo == "Rango Personalizado":
            # Rango por defecto: últimos 30 días a hoy
            fecha_defecto_inicio = (hoy - timedelta(days=30)).date()
            fecha_defecto_fin = hoy.date()
            
            rango_fechas = st.date_input(
                "Selecciona el rango (Inicio - Fin):", 
                [fecha_defecto_inicio, fecha_defecto_fin],
                help="Asegúrate de seleccionar tanto la fecha de inicio como la de fin en el calendario."
            )
            
            # Validar si el usuario seleccionó ambas fechas o está en proceso (un solo clic)
            if isinstance(rango_fechas, (list, tuple)):
                if len(rango_fechas) == 2:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[1], datetime.max.time())
                elif len(rango_fechas) == 1:
                    fecha_inicio = datetime.combine(rango_fechas[0], datetime.min.time())
                    fecha_fin = datetime.combine(rango_fechas[0], datetime.max.time())
            else:
                fecha_inicio = datetime.combine(rango_fechas, datetime.min.time())
                fecha_fin = datetime.combine(rango_fechas, datetime.max.time())
                
            st.info(f"Rango activo: **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**")
        else:
            st.info("Mostrando la totalidad de los datos registrados.")

    # Aplicar el filtro de fechas de manera exacta eliminando conflictos de zona horaria
    df_filtrado = df_finanzas.copy()
    if periodo != "Todo el Historial":
        if df_filtrado['fecha'].dt.tz is not None:
            df_filtrado['fecha'] = df_filtrado['fecha'].dt.tz_localize(None)
            
        df_filtrado = df_filtrado[
            (df_filtrado['fecha'] >= pd.to_datetime(fecha_inicio)) & 
            (df_filtrado['fecha'] <= pd.to_datetime(fecha_fin))
        ]

    st.write("---")

    # ---------------------------------------------------------
    # CÁLCULO DE MÉTRICAS CLAVE
    # ---------------------------------------------------------
    # Filtros por tipo de movimiento (Ignorando mayúsculas/minúsculas)
    ingresos_df = df_filtrado[df_filtrado['tipo'].str.lower() == 'ingreso']
    egresos_df = df_filtrado[df_filtrado['tipo'].str.lower() == 'egreso']

    total_ingresos = ingresos_df['monto'].sum()
    total_egresos = egresos_df['monto'].sum()
    balance_neto = total_ingresos - total_egresos

    # Despliegue de tarjetas de KPI
    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        st.metric(
            label="🟢 Total Ingresos", 
            value=f"$ {total_ingresos:,.2f}"
        )
    with kpi2:
        st.metric(
            label="🔴 Total Egresos (Gastos)", 
            value=f"$ {total_egresos:,.2f}"
        )
    with kpi3:
        # Color dinámico si el balance es positivo o negativo
        if balance_neto >= 0:
            st.metric(label="💰 Balance Neto", value=f"$ {balance_neto:,.2f}")
        else:
            st.metric(label="💰 Balance Neto", value=f"$ {balance_neto:,.2f}", delta_color="inverse")

    st.write("---")

    # ---------------------------------------------------------
    # SECCIÓN GRÁFICA Y DESGLOSE POR CATEGORÍAS
    # ---------------------------------------------------------
    col_tabla, col_grafica = st.columns([3, 2])

    with col_tabla:
        st.subheader("📋 Registros del Período")
        
        # Formatear la tabla para una lectura más cómoda
        df_mostrar = df_filtrado.copy()
        if not df_mostrar.empty:
            df_mostrar['fecha'] = df_mostrar['fecha'].dt.strftime('%d/%m/%Y %H:%M')
            df_mostrar['monto'] = df_mostrar['monto'].map('$ {:,.2f}'.format)
            
            # Reordenar y limpiar columnas visibles
            columnas_visibles = [c for c in ['fecha', 'concepto', 'tipo', 'categoria', 'monto', 'nota'] if c in df_mostrar.columns]
            st.dataframe(df_mostrar[columnas_visibles], use_container_width=True, hide_index=True)
        else:
            st.write("No se encontraron movimientos registrados en las fechas seleccionadas.")

    with col_grafica:
        st.subheader("📊 Distribución por Categorías")
        
        if not df_filtrado.empty:
            # Agrupar los gastos por su categoría de destino
            categoria_df = df_filtrado.groupby(['categoria', 'tipo'])['monto'].sum().reset_index()
            
            if not categoria_df.empty:
                st.bar_chart(
                    data=categoria_df,
                    x='categoria',
                    y='monto',
                    color='tipo',
                    use_container_width=True
                )
            else:
                st.write("Faltan datos categóricos para estructurar el gráfico.")
        else:
            st.write("Sin datos gráficos para el rango seleccionado.")

    # ---------------------------------------------------------
    # BOTÓN DE REFRESCADO MANUAL
    # ---------------------------------------------------------
    st.write("---")
    if st.button("🔄 Forzar Actualización de Datos"):
        st.cache_data.clear()
        st.rerun()
