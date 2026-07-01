import streamlit as st
import os
import uuid
import json
from datetime import datetime

from app.pdf_extract import extract_text_blocks
from app.ai_verifier import evaluate_project_with_ai
from app.report import render_html_report, render_pdf_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAVICON_PATH = os.path.join(os.path.dirname(BASE_DIR), "public", "favicon.ico")

st.set_page_config(
    page_title="IANA - Validador de Proyectos (OGUC)",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else "🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS = os.path.join(DATA_DIR, "uploads")
RESULTS = os.path.join(DATA_DIR, "results")
OGUC_PATH = os.path.join(BASE_DIR, "knowledge", "OGUC_2026.md")

os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

st.title("IANA v0.1 — Validador Normativo de Proyectos")
st.markdown("Verifica planos y especificaciones técnicas contra la **Ordenanza General de Urbanismo y Construcción (OGUC) de Chile** utilizando Inteligencia Artificial.")

@st.cache_data
def load_oguc_in_memory():
    if os.path.exists(OGUC_PATH):
        with open(OGUC_PATH, "r", encoding="utf-8") as handle:
            return handle.read()
    else:
        alt_path = os.path.join(os.path.dirname(BASE_DIR), "knowledge", "OGUC_2026.md")
        if os.path.exists(alt_path):
            with open(alt_path, "r", encoding="utf-8") as handle:
                return handle.read()
    return ""

OGUC_CONTENT = load_oguc_in_memory()
if not OGUC_CONTENT:
    st.error("Error al cargar el archivo OGUC_2026.md.")

def get_jobs_history():
    if not os.path.exists(RESULTS):
        return []
    files = [f for f in os.listdir(RESULTS) if f.endswith(".json")]
    history = []
    for f in files:
        path = os.path.join(RESULTS, f)
        try:
            mtime = os.path.getmtime(path)
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            history.append({
                "job_id": data.get("job_id"),
                "filename": data.get("filename"),
                "project_name": data.get("project_name", data.get("filename")),
                "success_probability": data.get("success_probability", 0.0),
                "mtime": mtime
            })
        except Exception:
            pass
    history.sort(key=lambda x: x["mtime"], reverse=True)
    return history

if "search_cache" not in st.session_state:
    st.session_state["search_cache"] = ""
if "limit" not in st.session_state:
    st.session_state["limit"] = 10

st.sidebar.markdown(
    """
    <style>
    .sidebar-title {
        margin-top: -45px;
        margin-bottom: 12px;
        font-size: 15px;
        font-weight: bold;
        color: #333333;
    }
    .sidebar-btn {
        display: block;
        width: 100%;
        padding: 5px 8px;
        margin-bottom: 4px;
        text-decoration: none !important;
        font-size: 12px;
        border-radius: 4px;
        box-sizing: border-box;
    }
    .btn-new {
        border: 1px solid #0066cc !important;
        color: #0066cc !important;
        background-color: #ffffff !important;
        font-weight: bold;
        text-align: center;
        margin-bottom: 12px;
    }
    .btn-new:hover {
        background-color: #f4f9ff !important;
    }
    .btn-item {
        border: 1px solid transparent;
        color: #444444 !important;
        background-color: transparent;
        text-align: left;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .btn-item:hover {
        background-color: #f0f2f6 !important;
        color: #111111 !important;
    }
    .btn-active {
        border: 1px solid #0066cc !important;
        color: #0066cc !important;
        background-color: #ffffff !important;
        font-weight: bold;
        text-align: left;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .recientes-title {
        margin-top: 10px;
        margin-bottom: 6px;
        font-size: 11px;
        color: #666666;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown('<div class="sidebar-title">Historial de análisis</div>', unsafe_allow_html=True)
st.sidebar.markdown('<a href="?" target="_self" class="sidebar-btn btn-new">Nuevo análisis</a>', unsafe_allow_html=True)
    
search_query = st.sidebar.text_input("Buscar", label_visibility="collapsed", placeholder="Buscar por título...")
if search_query != st.session_state["search_cache"]:
    st.session_state["search_cache"] = search_query
    st.session_state["limit"] = 10
    st.rerun()

st.sidebar.markdown('<div class="recientes-title">Recientes</div>', unsafe_allow_html=True)

history_jobs = get_jobs_history()

if search_query:
    filtered_jobs = [
        j for j in history_jobs
        if search_query.lower() in j["project_name"].lower() or search_query.lower() in j["filename"].lower()
    ]
else:
    filtered_jobs = history_jobs

limit = st.session_state["limit"]
sliced_jobs = filtered_jobs[:limit]
active_job_id = st.query_params.get("job_id")

recent_html = '<div style="max-height: 380px; overflow-y: auto; padding-right: 2px; margin-bottom: 8px;">'
for j in sliced_jobs:
    is_active = (active_job_id == j["job_id"])
    css_class = "btn-active" if is_active else "btn-item"
    title_text = f"{j['project_name']} ({j['success_probability']:.1f}%)"
    recent_html += f'<a href="?job_id={j["job_id"]}" target="_self" class="sidebar-btn {css_class}" title="{title_text}">{title_text}</a>'
recent_html += '</div>'

st.sidebar.markdown(recent_html, unsafe_allow_html=True)

if len(filtered_jobs) > limit:
    if st.sidebar.button("Cargar más", use_container_width=True):
        st.session_state["limit"] = limit + 10
        st.rerun()

def display_results(result_data):
    st.success(f"Análisis del proyecto completado: **{result_data['project_name']}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Viabilidad Normativa",
            value=f"{result_data['success_probability']:.1f}%",
        )
    with col2:
        st.metric(
            label="Infracciones Detectadas",
            value=len(result_data.get("infractions", []))
        )
    with col3:
        st.metric(
            label="Estado de Viabilidad",
            value="Aprobado con obs." if len(result_data.get("infractions", [])) > 0 else "Aprobado",
        )
        
    st.subheader("Resumen Ejecutivo", anchor=False)
    st.info(result_data.get("summary_notes", "Sin notas del análisis."))

    st.subheader("Detalle de Infracciones de la OGUC", anchor=False)
    infractions = result_data.get("infractions", [])
    
    if infractions:
        for idx, inf in enumerate(infractions):
            severity = inf.get("severity", "ALTA")
            color = "red" if severity == "ALTA" else "orange" if severity == "MEDIA" else "blue"
            
            emoji = "🔴" if severity == "ALTA" else "🟠" if severity == "MEDIA" else "🔵"
            with st.expander(f"{emoji} [{severity}] {inf.get('rule_id')} - {inf.get('description')[:80]}..."):
                st.markdown(f"**Artículo OGUC:** `{inf.get('rule_id')}`")
                st.markdown(f"**Severidad:** :{color}[{severity}]")
                st.markdown(f"**Evidencia en documento:** `{inf.get('evidence')}`")
                st.markdown(f"**Justificación legal:** {inf.get('justification')}")
                st.markdown(f"**Descripción completa:** {inf.get('description')}")
    else:
        st.success("No se detectaron infracciones a la OGUC de Chile en este documento.")

    st.subheader("Descargar Reportes", anchor=False)
    
    html_content = render_html_report(result_data["filename"], result_data)
    try:
        pdf_content = render_pdf_report(result_data["filename"], result_data)
    except Exception as e:
        pdf_content = None
        st.error(f"Error al generar el PDF: {e}")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="Descargar Reporte HTML Interactivo",
            data=html_content,
            file_name=f"reporte_iana_{result_data['job_id']}.html",
            mime="text/html",
            use_container_width=True
        )
    with col_d2:
        if pdf_content:
            st.download_button(
                label="Imprimir Reporte PDF",
                data=pdf_content,
                file_name=f"reporte_iana_{result_data['job_id']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.button("PDF Report (No disponible)", disabled=True, use_container_width=True)

if active_job_id is None:
    st.subheader("Subir Documentación de Proyecto", anchor=False)
    uploaded_file = st.file_uploader(
        "Sube el plano o las especificaciones técnicas del proyecto en formato PDF:",
        type=["pdf"],
        help="El archivo debe tener texto seleccionable (no imágenes puras sin OCR)."
    )

    if uploaded_file is not None:
        st.info(f"Archivo cargado: **{uploaded_file.name}** ({uploaded_file.size / 1024:.2f} KB)")
        
        if st.button("🔍 Iniciar Validación Normativa con IA", type="primary"):
            job_id = str(uuid.uuid4())
            pdf_path = os.path.join(UPLOADS, f"{job_id}.pdf")
            
            with st.spinner("Guardando archivo PDF..."):
                with open(pdf_path, "wb") as handle:
                    handle.write(uploaded_file.getbuffer())
                    
            with st.spinner("Extrayendo texto del PDF..."):
                try:
                    blocks = extract_text_blocks(pdf_path)
                    plan_text = "\n".join([b.text for b in blocks])
                except Exception as e:
                    st.error(f"Error extrayendo texto del PDF: {e}")
                    st.stop()
                    
            if not plan_text.strip():
                st.error("⚠️ El PDF no contiene texto seleccionable. Asegúrate de que no sea una imagen escaneada sin OCR.")
                st.stop()
                
            with st.spinner("Analizando y comparando con la OGUC de Chile (Gemini API)..."):
                try:
                    evaluation = evaluate_project_with_ai(plan_text, OGUC_CONTENT)
                    eval_dict = evaluation.model_dump()
                except Exception as e:
                    st.error(f"Error llamando a la API de Gemini o procesando con Instructor: {e}")
                    st.stop()
            
            result_data = {
                "job_id": job_id,
                "filename": uploaded_file.name,
                "project_name": eval_dict.get("project_name", uploaded_file.name),
                "success_probability": eval_dict.get("success_probability", 0.0),
                "infractions": eval_dict.get("infractions", []),
                "summary_notes": eval_dict.get("summary_notes", ""),
            }
            
            out_json = os.path.join(RESULTS, f"{job_id}.json")
            with open(out_json, "w", encoding="utf-8") as handle:
                json.dump(result_data, handle, ensure_ascii=False, indent=2)

            out_html = os.path.join(RESULTS, f"{job_id}.html")
            with open(out_html, "w", encoding="utf-8") as handle:
                handle.write(render_html_report(uploaded_file.name, result_data))
                
            st.query_params["job_id"] = job_id
            st.rerun()

else:
    path = os.path.join(RESULTS, f"{active_job_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            result_data = json.load(handle)
        display_results(result_data)
    else:
        st.error("No se encontró el archivo de resultados seleccionado.")