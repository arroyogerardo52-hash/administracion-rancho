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
    st.caption("Análisis financiero interactivo basado en la estructura de costos de tu rancho.")

    # 1. CARGA DE DATOS DESDE SUPABASE
    df = cargar_datos_finanzas(supabase)

    # Categorías estándar
    cat_costos_directos = ["Compra de ganado", "Alimentos", "Medicamentos", "Servicios veterinarios", "Dosis de semen", "Varios (Costos directos)"]
    cat_gastos_operativos = ["Gastos de oficina", "Arriendo", "Nomina", "Combustible", "Mantenimiento", "Pago / Abono Préstamo", "Varios (Gastos operativos)"]

    # Totales Históricos
    costos_fijos_historicos = 0.0
    costos_directos_historicos = 0.0
    ingresos_historicos = 0.0

    if not df.empty and 'monto' in df.columns:
        df['tipo_str'] = df['tipo'].astype(str).str.lower() if 'tipo' in df.columns else ""
        df['cat_str'] = df['categoria'].astype(str) if 'categoria' in df.columns else ""

        costos_fijos_historicos = df[df['cat_str'].isin(cat_gastos_operativos)]['monto'].sum()
        costos_directos_historicos = df[df['cat_str'].isin(cat_costos_directos)]['monto'].sum()
        ingresos_historicos = df[df['tipo_str'].str.contains('ingreso')]['monto'].sum()

    # 2. CONTROLES Y PARÁMETROS
    st.subheader("⚙️ Parámetros para la Proyección")
    st.info("💡 **Tip:** Ajusta los valores por animal (costo directo promedio y precio proyectado) para calcular tu punto de equilibrio real.")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        costo_fijo = st.number_input(
            "Gastos Operativos / Fijos ($)", 
            value=float(costos_fijos_historicos) if costos_fijos_historicos > 0 else 100000.0, 
            step=5000.0,
            help="Estructura de costos fijos a cubrir (Nómina, Arriendo, Combustibles, etc.)."
        )
    with col2:
        costo_var_unitario = st.number_input(
            "Costo Variable por Animal ($)", 
            value=10000.0, 
            step=500.0,
            help="Lo que te cuesta engordar/producir 1 animal (Alimentos, vacunas, compra inicial)."
        )
    with col3:
        precio_venta_unitario = st.number_input(
            "Precio Venta Proyectado por Animal ($)", 
            value=18000.0, 
            step=500.0,
            help="Precio estimado al que venderás cada animal."
        )

    # 3. PESTAÑAS DE ANÁLISIS
    tab1, tab2, tab3 = st.tabs(["⚖️ Punto de Equilibrio", "🔀 Escenarios", "📋 Resumen Histórico"])

    with tab1:
        st.markdown("### Calculadora de Punto de Equilibrio")
        
        margen_contribucion = precio_venta_unitario - costo_var_unitario

        if margen_contribucion <= 0:
            st.error("⚠️ El precio de venta por animal debe ser mayor al costo variable unitario para generar ganancia.")
        else:
            unidades_equilibrio = int(costo_fijo / margen_contribucion) + 1
            ventas_equilibrio = unidades_equilibrio * precio_venta_unitario

            m1, m2, m3 = st.columns(3)
            m1.metric("Cabezas Necesarias para Equilibrio", f"{unidades_equilibrio} cabezas")
            m2.metric("Ventas Totales Requeridas", f"${ventas_equilibrio:,.2f} MXN")
            m3.metric("Ganancia Neta por Animal (Margen)", f"${margen_contribucion:,.2f} MXN")

            # Gráfica Plotly
            max_unidades = max(int(unidades_equilibrio * 1.8), 30)
            paso = max(1, max_unidades // 15)
            unidades_range = list(range(0, max_unidades + 1, paso))

            df_grafico = pd.DataFrame({
                "Cabezas": unidades_range,
                "Costos Fijos": [costo_fijo] * len(unidades_range),
                "Costos Totales": [costo_fijo + (u * costo_var_unitario) for u in unidades_range],
                "Ingresos Totales": [u * precio_venta_unitario for u in unidades_range]
            })

            fig = px.line(
                df_grafico, 
                x="Cabezas", 
                y=["Costos Fijos", "Costos Totales", "Ingresos Totales"],
                labels={"value": "Monto ($ MXN)", "variable": "Concepto", "Cabezas": "Número de Cabezas / Animales"},
                title="Punto de Equilibrio: Ingresos vs Costos Totales"
            )
            
            # Formato estético del gráfico
            fig.update_layout(hovermode="x unified", legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### Comparador de Escenarios de Venta")
        
        volumen_estimado = st.slider(
            "Selecciona un Volumen de Venta Proyectado (Cabezas):", 
            min_value=1, 
            max_value=150, 
            value=max(int(unidades_equilibrio) if 'unidades_equilibrio' in locals() else 20, 10)
        )

        escenarios = {
            "Conservador (-15% Precio)": precio_venta_unitario * 0.85,
            "Base (Precio Objetivo)": precio_venta_unitario,
            "Optimista (+15% Precio)": precio_venta_unitario * 1.15
        }

        res_escenarios = []
        for nombre, px_venta in escenarios.items():
            ingreso_total = volumen_estimado * px_venta
            costo_total = costo_fijo + (volumen_estimado * costo_var_unitario)
            utilidad = ingreso_total - costo_total
            res_escenarios.append({
                "Escenario": nombre,
                "Precio Venta / Cabeza": f"${px_venta:,.2f} MXN",
                "Ingresos Totales": f"${ingreso_total:,.2f} MXN",
                "Costos Totales": f"${costo_total:,.2f} MXN",
                "Utilidad / Pérdida Neta": f"${utilidad:,.2f} MXN"
            })

        st.table(pd.DataFrame(res_escenarios))

    with tab3:
        st.markdown("### Resumen de Registros Reales de Supabase")
        if not df.empty:
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total Ingresos Registrados", f"${ingresos_historicos:,.2f} MXN")
            col_b.metric("Total Costos Directos", f"${costos_directos_historicos:,.2f} MXN")
            col_c.metric("Total Gastos Operativos", f"${costos_fijos_historicos:,.2f} MXN")
            
            st.markdown("---")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No se encontraron registros previos en la tabla 'finanzas'.")
