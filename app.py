import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import time
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Rancho AE - Administración", page_icon="🤠", layout="wide")

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

# ==========================================
# 4. FUNCIÓN PARA GENERAR REPORTE PDF EDITABLE
# ==========================================
def generar_pdf_reporte(titulo, df_data, notas_adicionales=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#2C3E50'),
        alignment=0,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#7F8C8D'),
        spaceAfter=15
    )
    
    heading_style = ParagraphStyle(
        'DocHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#16A085'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12
    )

    # Encabezado del documento
    story.append(Paragraph(f"<b>Rancho AE</b> - {titulo}", title_style))
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Fecha de generación: {fecha_str}", subtitle_style))
    story.append(Spacer(1, 10))

    # Tabla de Datos
    if not df_data.empty:
        headers = [str(col).capitalize() for col in df_data.columns]
        table_data = [[Paragraph(f"<b>{h}</b>", body_style) for h in headers]]
        
        for _, row in df_data.iterrows():
            row_cells = [Paragraph(str(val) if pd.notna(val) else "", body_style) for val in row]
            table_data.append(row_cells)

        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EAECEE')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#2C3E50')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BDC3C7')),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("<i>No hay registros disponibles para mostrar.</i>", body_style))

    story.append(Spacer(1, 15))
    story.append(Paragraph("Campos / Notas Editables", heading_style))

    # Agregar campos de formulario interactivo (AcroForm) al PDF
    def add_interactive_fields(canvas_obj, doc_obj):
        canvas_obj.saveState()
        form = canvas_obj.acroForm
        
        # Campo para observaciones editables
        form.textfield(
            name='notas_observaciones',
            tooltip='Ingresa observaciones o comentarios aquí',
            x=36, y=100,
            width=540, height=50,
            borderStyle='solid',
            borderColor=colors.HexColor('#BDC3C7'),
            fillColor=colors.HexColor('#FAFAFA'),
            textColor=colors.HexColor('#2C3E50'),
            forceBorder=True
        )
        
        # Campo para firma/nombre editable
        form.textfield(
            name='firma_responsable',
            tooltip='Nombre del Responsable',
            x=36, y=40,
            width=250, height=20,
            borderStyle='solid',
            borderColor=colors.HexColor('#BDC3C7'),
            fillColor=colors.HexColor('#FAFAFA'),
            textColor=colors.HexColor('#2C3E50'),
            forceBorder=True
        )
        
        canvas_obj.drawString(36, 155, "Notas / Observaciones del Reporte (editable):")
        canvas_obj.drawString(36, 65, "Nombre y Firma del Responsable (editable):")
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=add_interactive_fields, onLaterPages=add_interactive_fields)
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# BARRA LATERAL: LOGO, NAVEGACIÓN Y RESPALDOS
# ==========================================
with st.sidebar:
    st.header("🏢 Imagen Corporativa")
    
    logo_file = st.file_uploader(
        "Sube el Logotipo (PNG/JPG):",
        type=["png", "jpg", "jpeg"],
        help="Selecciona una imagen desde tu computadora o celular"
    )
    
    logo_html_src = ""
    if logo_file is not None:
        try:
            bytes_data = logo_file.getvalue()
            base64_encoded = base64.b64encode(bytes_data).decode("utf-8")
            mime_type = logo_file.type
            logo_html_src = f"data:{mime_type};base64,{base64_encoded}"
            st.image(bytes_data, width=140, caption="Logotipo cargado")
        except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")
    else:
        logo_html_src = "https://images.unsplash.com/photo-1516467508483-a7212febe31a?q=80&w=200&auto=format&fit=crop"
        st.info("💡 Usando logo predeterminado temporalmente.")
    
    st.markdown("---")
    st.header("📊 Generar Reportes PDF")
    
    opcion_reporte = st.selectbox("Selecciona la tabla a exportar:", ["Finanzas", "Empleados", "Clientes", "Proveedores", "Lotes"])
    
    df_map = {
        "Finanzas": df_finanzas,
        "Empleados": df_empleados,
        "Clientes": df_clientes,
        "Proveedores": df_proveedores,
        "Lotes": df_lotes
    }
    
    if st.button(f"📄 Generar PDF Editable - {opcion_reporte}"):
        df_selected = df_map[opcion_reporte]
        pdf_bytes = generar_pdf_reporte(f"Reporte de {opcion_reporte}", df_selected)
        
        st.download_button(
            label=f"⬇️ Descargar Reporte PDF Editable ({opcion_reporte})",
            data=pdf_bytes,
            file_name=f"Reporte_{opcion_reporte}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
