import streamlit as st
import pandas as pd
from datetime import datetime
import json
import io

st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")
st.title("🤠 Rancho AE: Sistema de Administración")
st.markdown("---")

# ==========================================
# CONEXIÓN INTERNA NATIIVA DE STREAMLIT CLOUD
# ==========================================

# Funciones para leer de los secretos internos de Streamlit
def cargar_tabla_interna(nombre_tabla):
    try:
        # Lee el texto en formato JSON guardado en tus secrets nativos
        datos_json = st.secrets["datos_rancho"][nombre_tabla]
        lista_datos = json.loads(datos_json)
        return pd.DataFrame(lista_datos)
    except Exception:
        return pd.DataFrame()

# Cargar la información directo del servicio de Streamlit
df_finanzas = cargar_tabla_interna("finanzas")
df_empleados = cargar_tabla_interna("empleados")
df_clientes = cargar_tabla_interna("clientes")
df_proveedores = cargar_tabla_interna("proveedores")
df_lotes = cargar_tabla_interna("lotes")
