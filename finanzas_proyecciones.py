import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def obtener_datos_gastos_supabase(supabase):
    """Obtiene los registros de la tabla 'finanzas' en Supabase y los agrupa por tipo_costo."""
    try:
        response = supabase.table("finanzas").select("*").execute()
        if not response.data:
            return 0.0, 0.0, pd.DataFrame()
        
        df = pd.DataFrame(response.data)
        
        # Filtrar solo egresos/gastos si la tabla 'finanzas' contiene ingresos y egresos
        if 'tipo_movimiento' in df.columns:
            df_gastos = df[df['tipo_movimiento'].str.lower() == 'gasto']
        elif 'tipo' in df.columns:
            df_gastos = df[df['tipo'].str.lower() == 'gasto']
        else:
            df_gastos = df

        costos_fijos = df_gastos[df_gastos['tipo_costo'] == 'fijo']['monto'].sum() if 'tipo_costo' in df_gastos.columns else 0.0
        costos_variables = df_gastos[df_gastos['tipo_costo'] == 'variable']['monto'].sum() if 'tipo_costo' in df_gastos.columns else 0.0
        
        return float(costos_fijos), float(costos_variables), df_gastos
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        return 0.0, 0.0, pd.DataFrame()


def render_vista_proyecciones_y_equilibrio(supabase):
    st.title("📊 Finanzas: Punto de Equilibrio y Proyecciones")
    st.caption("Herramienta de simulación y análisis financiero basada en tus datos de Supabase.")

    # Cargar datos base desde Supabase
    c_fijos_real, c_vars_real, df_gastos = obtener_datos_gastos_supabase(supabase)

    # Definición de pestañas
    tab_simulador, tab_escenarios, tab_desglose = st.tabs([
        "⚖️ Punto de Equilibrio & Proyección", 
        "🔀 Comparador de Escenarios", 
        "📋 Desglose de Gastos"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: PUNTO DE EQUILIBRIO Y PROYECCIÓN INDIVIDUAL
    # -------------------------------------------------------------------------
    with tab_simulador:
        st.subheader("1. Parámetros Operativos Base")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            costos_fijos = st.number_input(
                "Costos Fijos Mensuales ($)", 
                value=c_fijos_real if c_fijos_real > 0 else 25000.0,
                step=1000.0,
                key="cf_base"
            )
        with col_f2:
            costo_var_unitario = st.number_input(
                "Costo Variable Unitario ($)", 
                value=1200.0, 
                step=50.0,
                key="cv_base"
            )
        with col_f3:
            precio_unitario = st.number_input(
                "Precio de Venta Unitario ($)", 
                value=2500.0, 
                step=50.0,
                key="p_base"
            )

        margen_unitario = precio_unitario - costo_var_unitario

        if margen_unitario <= 0:
            st.error("⚠️ El precio de venta debe ser superior al costo variable unitario para generar margen positivo.")
        else:
            q_equilibrio = costos_fijos / margen_unitario
            ingresos_equilibrio = q_equilibrio * precio_unitario

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Punto de Equilibrio (Q)", f"{q_equilibrio:.1f} Unidades")
            m2.metric("Ingreso Requerido", f"${ingresos_equilibrio:,.2f}")
            m3.metric("Margen por Unidad", f"${margen_unitario:,.2f}")
            m4.metric("Margen de Contribución", f"{(margen_unitario/precio_unitario)*100:.1f}%")

            st.subheader("2. Gráfico de Punto de Equilibrio")
            ventas_esperadas = st.slider(
                "Simular Ventas Mensuales (Unidades):", 
                min_value=1, 
                max_value=int(q_equilibrio * 3) if q_equilibrio > 0 else 100, 
                value=int(q_equilibrio * 1.3) if q_equilibrio > 0 else 30,
                key="ventas_sim"
            )

            max_q = max(int(q_equilibrio * 2), ventas_esperadas + 5)
            rango_q = list(range(0, max_q + 1))

            df_chart = pd.DataFrame({
                "Unidades": rango_q,
                "Costos Totales": [costos_fijos + (q * costo_var_unitario) for q in rango_q],
                "Ingresos": [q * precio_unitario for q in rango_q]
            })

            fig = px.line(
                df_chart, x="Unidades", y=["Costos Totales", "Ingresos"],
                title="Relación de Ingresos vs Costos Totales",
                color_discrete_map={"Costos Totales": "#E74C3C", "Ingresos": "#2ECC71"}
            )
            fig.add_vline(x=q_equilibrio, line_dash="dash", line_color="#34495E", annotation_text=f"P.E. ({q_equilibrio:.1f} u)")
            fig.add_vline(x=ventas_esperadas, line_dash="dot", line_color="#2980B9", annotation_text=f"Meta ({ventas_esperadas} u)")
            st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 2: COMPARADOR MULTI-ESCENARIO
    # -------------------------------------------------------------------------
    with tab_escenarios:
        st.subheader("🔀 Análisis de Sensibilidad y Comparación de Escenarios")
        st.caption("Ajusta los factores de variación para evaluar la resiliencia del negocio.")

        # Controles de variación
        c_esc1, c_esc2, c_esc3 = st.columns(3)
        
        with c_esc1:
            st.markdown("### 🟡 Conservador (Base)")
            st.write(f"• **Costos Fijos:** ${costos_fijos:,.2f}")
            st.write(f"• **Costo Var. Unitario:** ${costo_var_unitario:,.2f}")
            st.write(f"• **Precio Unitario:** ${precio_unitario:,.2f}")
            q_ventas_cons = st.number_input("Ventas estimadas (unidades)", value=ventas_esperadas, key="v_cons")

        with c_esc2:
            st.markdown("### 🟢 Optimista")
            inc_precio_opt = st.slider("Incremento en Precio (%)", 0.0, 30.0, 10.0, step=1.0) / 100
            red_costo_opt = st.slider("Reducción Costo Variable (%)", 0.0, 20.0, 5.0, step=1.0) / 100
            q_ventas_opt = st.number_input("Ventas estimadas (unidades)", value=int(ventas_esperadas * 1.15), key="v_opt")

        with c_esc3:
            st.markdown("### 🔴 Crítico / Riesgo")
            inc_costo_crit = st.slider("Incremento Costos Variables (%)", 0.0, 40.0, 15.0, step=1.0) / 100
            inc_fijos_crit = st.slider("Incremento Costos Fijos (%)", 0.0, 30.0, 10.0, step=1.0) / 100
            q_ventas_crit = st.number_input("Ventas estimadas (unidades)", value=int(ventas_esperadas * 0.85), key="v_crit")

        # CÁLCULOS COMPARATIVOS
        # 1. Conservador
        p_cons = precio_unitario
        cv_cons = costo_var_unitario
        cf_cons = costos_fijos
        m_cons = p_cons - cv_cons
        pe_cons = cf_cons / m_cons if m_cons > 0 else 0
        util_cons = (q_ventas_cons * m_cons) - cf_cons
        ms_cons = ((q_ventas_cons - pe_cons) / q_ventas_cons * 100) if q_ventas_cons > 0 else 0

        # 2. Optimista
        p_opt = precio_unitario * (1 + inc_precio_opt)
        cv_opt = costo_var_unitario * (1 - red_costo_opt)
        cf_opt = costos_fijos
        m_opt = p_opt - cv_opt
        pe_opt = cf_opt / m_opt if m_opt > 0 else 0
        util_opt = (q_ventas_opt * m_opt) - cf_opt
        ms_opt = ((q_ventas_opt - pe_opt) / q_ventas_opt * 100) if q_ventas_opt > 0 else 0

        # 3. Crítico
        p_crit = precio_unitario
        cv_crit = costo_var_unitario * (1 + inc_costo_crit)
        cf_crit = costos_fijos * (1 + inc_fijos_crit)
        m_crit = p_crit - cv_crit
        pe_crit = cf_crit / m_crit if m_crit > 0 else 0
        util_crit = (q_ventas_crit * m_crit) - cf_crit
        ms_crit = ((q_ventas_crit - pe_crit) / q_ventas_crit * 100) if q_ventas_crit > 0 else 0

        st.markdown("---")
        st.subheader("Tabla Comparativa de Resultados")

        df_escenarios = pd.DataFrame({
            "Métrica": [
                "Precio de Venta ($)", 
                "Costo Variable Unitario ($)", 
                "Costos Fijos Totales ($)",
                "Margen Unitario ($)", 
                "Punto de Equilibrio (Unidades)", 
                "Ventas Proyectadas (Unidades)",
                "Margen de Seguridad (%)", 
                "Utilidad Neta Mensual ($)"
            ],
            "🟡 Conservador": [
                f"${p_cons:,.2f}", f"${cv_cons:,.2f}", f"${cf_cons:,.2f}",
                f"${m_cons:,.2f}", f"{pe_cons:.1f} u", f"{q_ventas_cons} u",
                f"{ms_cons:.1f}%", f"${util_cons:,.2f}"
            ],
            "🟢 Optimista": [
                f"${p_opt:,.2f}", f"${cv_opt:,.2f}", f"${cf_opt:,.2f}",
                f"${m_opt:,.2f}", f"{pe_opt:.1f} u", f"{q_ventas_opt} u",
                f"{ms_opt:.1f}%", f"${util_opt:,.2f}"
            ],
            "🔴 Crítico": [
                f"${p_crit:,.2f}", f"${cv_crit:,.2f}", f"${cf_crit:,.2f}",
                f"${m_crit:,.2f}", f"{pe_crit:.1f} u", f"{q_ventas_crit} u",
                f"{ms_crit:.1f}%", f"${util_crit:,.2f}"
            ]
        })

        st.dataframe(df_escenarios, use_container_width=True, hide_index=True)

        # Gráfico comparativo de Utilidad Neta por Escenario
        df_chart_util = pd.DataFrame({
            "Escenario": ["Conservador", "Optimista", "Crítico"],
            "Utilidad Neta ($)": [util_cons, util_opt, util_crit],
            "Punto de Equilibrio (u)": [pe_cons, pe_opt, pe_crit]
        })

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_bar_util = px.bar(
                df_chart_util, x="Escenario", y="Utilidad Neta ($)",
                title="Comparativa de Utilidad Neta Mensual",
                color="Escenario",
                color_discrete_map={"Conservador": "#F39C12", "Optimista": "#2ECC71", "Crítico": "#E74C3C"}
            )
            st.plotly_chart(fig_bar_util, use_container_width=True)

        with col_g2:
            fig_bar_pe = px.bar(
                df_chart_util, x="Escenario", y="Punto de Equilibrio (u)",
                title="Exigencia de Unidades (Punto de Equilibrio)",
                color="Escenario",
                color_discrete_map={"Conservador": "#F39C12", "Optimista": "#2ECC71", "Crítico": "#E74C3C"}
            )
            st.plotly_chart(fig_bar_pe, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 3: DESGLOSE DE GASTOS BASE DE SUPABASE
    # -------------------------------------------------------------------------
    with tab_desglose:
        st.subheader("Resumen de Registros en Supabase (Tabla Finanzas)")
        if not df_gastos.empty:
            c_f, c_v = st.columns(2)
            c_f.metric("Total Gastos Fijos Registrados", f"${c_fijos_real:,.2f}")
            c_v.metric("Total Gastos Variables Registrados", f"${c_vars_real:,.2f}")
            st.dataframe(df_gastos, use_container_width=True)
        else:
            st.info("No hay gastos registrados en la base de datos de Supabase aún.")
