import streamlit as st
import pandas as pd
import plotly.express as px

def cargar_datos_finanzas(supabase):
    """Consulta la tabla 'finanzas' en Supabase y devuelve un DataFrame estructurado."""
    try:
        res = supabase.table("finanzas").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            if 'monto' in df.columns:
                df['monto'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0.0)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de finanzas: {e}")
        return pd.DataFrame()

def render_vista_proyecciones_y_equilibrio(supabase):
    st.title("📈 Proyecciones & Punto de Equilibrio")
    st.caption("Análisis financiero automatizado basado en los registros reales de tu base de datos.")

    # 1. CARGA DE DATOS DESDE SUPABASE
    df = cargar_datos_finanzas(supabase)

    # Definición de categorías estándar del sistema
    cat_costos_directos = ["Compra de ganado", "Alimentos", "Medicamentos", "Servicios veterinarios", "Dosis de semen", "Varios (Costos directos)"]
    cat_gastos_operativos = ["Gastos de oficina", "Arriendo", "Nomina", "Combustible", "Mantenimiento", "Pago / Abono Préstamo", "Varios (Gastos operativos)"]

    # 2. CÁLCULO AUTOMÁTICO DE VALORES BASE
    costos_fijos_auto = 0.0
    costos_variables_auto = 0.0
    ingresos_totales_auto = 0.0

    if not df.empty and 'monto' in df.columns:
        # Normalizar nombres de columnas
        df['tipo_str'] = df['tipo'].astype(str).str.lower() if 'tipo' in df.columns else ""
        df['cat_str'] = df['categoria'].astype(str) if 'categoria' in df.columns else ""

        # Egresos fijos (Gastos operativos)
        df_fijos = df[df['cat_str'].isin(cat_gastos_operativos)]
        costos_fijos_auto = df_fijos['monto'].sum() if not df_fijos.empty else 0.0

        # Egresos variables (Costos directos de producción/ganado)
        df_variables = df[df['cat_str'].isin(cat_costos_directos)]
        costos_variables_auto = df_variables['monto'].sum() if not df_variables.empty else 0.0

        # Ingresos totales
        df_ingresos = df[df['tipo_str'].str.contains('ingreso')]
        ingresos_totales_auto = df_ingresos['monto'].sum() if not df_ingresos.empty else 0.0

    # 3. INTERFAZ DE PARÁMETROS (PRELLENADA PERO EDITABLE)
    st.subheader("⚙️ Parámetros del Análisis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        costo_fijo = st.number_input(
            "Costos Fijos Totales ($)", 
            value=float(costos_fijos_auto), 
            step=1000.0,
            help="Suma automática de tus gastos operativos registrados (Nómina, Arriendo, Combustible, etc.)."
        )
    with col2:
        costo_var_unitario = st.number_input(
            "Costo Variable Promedio por Unidad ($)", 
            value=float(costos_variables_auto) if costos_variables_auto > 0 else 5000.0, 
            step=500.0,
            help="Suma de costos directos registrados (Alimentos, Medicamentos, Compras)."
        )
    with col3:
        precio_venta_unitario = st.number_input(
            "Precio Promedio de Venta por Unidad ($)", 
            value=15000.0, 
            step=1000.0,
            help="Precio promedio estimado por venta de animal o producto."
        )

    # 4. PESTAÑAS DE ANÁLISIS
    tab1, tab2, tab3 = st.tabs(["⚖️ Punto de Equilibrio", "🔀 Escenarios", "📋 Resumen de Registros"])

    with tab1:
        st.markdown("### Calculadora de Punto de Equilibrio")
        
        margen_contribucion = precio_venta_unitario - costo_var_unitario

        if margen_contribucion <= 0:
            st.error("⚠️ El precio de venta debe ser mayor al costo variable por unidad para obtener un punto de equilibrio válido.")
        else:
            unidades_equilibrio = costo_fijo / margen_contribucion
            ventas_equilibrio = unidades_equilibrio * precio_venta_unitario

            m1, m2, m3 = st.columns(3)
            m1.metric("Unidades Necesarias", f"{int(unidades_equilibrio) + 1} cabezas / prod.")
            m2.metric("Ventas para Equilibrio", f"${ventas_equilibrio:,.2f}")
            m3.metric("Margen por Unidad", f"${margen_contribucion:,.2f}")

            # Gráfico de proyección
            max_unidades = int(unidades_equilibrio * 2) if unidades_equilibrio > 0 else 50
            unidades_range = list(range(0, max_unidades + 1, max(1, max_unidades // 20)))

            df_grafico = pd.DataFrame({
                "Unidades": unidades_range,
                "Costos Fijos": [costo_fijo] * len(unidades_range),
                "Costos Totales": [costo_fijo + (u * costo_var_unitario) for u in unidades_range],
                "Ingresos Totales": [u * precio_venta_unitario for u in unidades_range]
            })

            fig = px.line(
                df_grafico, 
                x="Unidades", 
                y=["Costos Fijos", "Costos Totales", "Ingresos Totales"],
                labels={"value": "Monto ($)", "variable": "Concepto"},
                title="Punto de Equilibrio: Ingresos vs Costos Totales"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### Comparador de Escenarios")
        st.write("Evalúa cómo cambia la rentabilidad ajustando los volúmenes de venta.")

        volumen_estimado = st.slider("Volumen Estimado de Ventas (Unidades/Cabezas):", 1, 100, int(unidades_equilibrio * 1.2) if 'unidades_equilibrio' in locals() and unidades_equilibrio > 0 else 20)

        # Escenarios: Conservador (-15%), Optimista (+15%), Base
        escenarios = {
            "Conservador (-15%)": precio_venta_unitario * 0.85,
            "Base (Actual)": precio_venta_unitario,
            "Optimista (+15%)": precio_venta_unitario * 1.15
        }

        res_escenarios = []
        for nombre, px_venta in escenarios.items():
            ingreso_total = volumen_estimado * px_venta
            costo_total = costo_fijo + (volumen_estimado * costo_var_unitario)
            utilidad = ingreso_total - costo_total
            res_escenarios.append({
                "Escenario": nombre,
                "Precio Venta": f"${px_venta:,.2f}",
                "Ingresos Totales": f"${ingreso_total:,.2f}",
                "Costos Totales": f"${costo_total:,.2f}",
                "Utilidad / Pérdida": f"${utilidad:,.2f}"
            })

        st.table(pd.DataFrame(res_escenarios))

    with tab3:
        st.markdown("### Registros Detectados en la Base de Datos")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total Ingresos Históricos", f"${ingresos_totales_auto:,.2f}")
            col_b.metric("Total Costos Directos", f"${costos_variables_auto:,.2f}")
            col_c.metric("Total Gastos Operativos", f"${costos_fijos_auto:,.2f}")
        else:
            st.info("No se encontraron registros previos en la tabla 'finanzas'. Agrega algunos ingresos y egresos en el Dashboard principal para alimentar este análisis automáticamente.")
