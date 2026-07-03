import streamlit as st
import os
import uuid
import json
from datetime import datetime

from app.pdf_extract import extract_text_blocks
from app.ai_verifier import (
    evaluate_project_with_ai,
    evaluate_document_individually,
    consolidate_project_context
)
from app.report import render_html_report, render_pdf_report
from app.db import (
    sign_in_user,
    sign_up_user,
    create_project,
    list_user_projects,
    upload_project_document,
    save_document_analysis,
    update_project_context_db
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAVICON_PATH = os.path.join(os.path.dirname(BASE_DIR), "public", "favicon.ico")

st.set_page_config(
    page_title="IANA - Validador de Proyectos (OGUC)",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS = os.path.join(DATA_DIR, "uploads")
RESULTS = os.path.join(DATA_DIR, "results")
OGUC_PATH = os.path.join(BASE_DIR, "knowledge", "OGUC_2026.md")

os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

if "user" not in st.session_state:
    st.session_state["user"] = None
if "jwt_token" not in st.session_state:
    st.session_state["jwt_token"] = None
if "projects" not in st.session_state:
    st.session_state["projects"] = []
if "active_project" not in st.session_state:
    st.session_state["active_project"] = None
if "show_create_project" not in st.session_state:
    st.session_state["show_create_project"] = False
if "search_cache" not in st.session_state:
    st.session_state["search_cache"] = ""
if "limit" not in st.session_state:
    st.session_state["limit"] = 10

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .sidebar-title {
        margin-top: -30px;
        margin-bottom: 12px;
        font-size: 16px;
        font-weight: bold;
        color: #1e293b;
    }
    .user-badge {
        background-color: #eff6ff;
        color: #1d4ed8;
        padding: 4px 8px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 12px;
        border: 1px solid #bfdbfe;
    }
    .project-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
    }
    .project-header {
        font-size: 22px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
    }
    .project-meta {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #0f172a;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
    st.error("Error crítico: No se pudo cargar el archivo normativo OGUC_2026.md.")

def render_auth_page():
    st.title("IANA v0.1 — Validador Normativo de Proyectos")
    st.markdown("Verifica planos y especificaciones técnicas contra la **Ordenanza General de Urbanismo y Construcción (OGUC) de Chile** utilizando Inteligencia Artificial.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(
            """
            ### ¿Qué es IANA?
            IANA permite automatizar la revisión de planos de arquitectura, especificaciones técnicas y CIPs (Certificados de Informaciones Previas).
            
            *   **Contexto Acumulativo de IA:** IANA analiza cada documento y actualiza de manera incremental el contexto del proyecto, permitiendo que un plano resuelva las alertas de una especificación técnica previa.
            *   **Seguridad RLS:** Acceso exclusivo a tus proyectos personales.
            *   **Resguardo de Experiencia:** En caso de fallas de conexión, tus archivos se respaldan localmente de inmediato para que sigas trabajando.
            """
        )
        
    with col2:
        auth_tab1, auth_tab2 = st.tabs(["Iniciar Sesión", "Crear Cuenta"])
        
        with auth_tab1:
            st.subheader("Acceder a IANA")
            login_email = st.text_input("Correo electrónico", key="login_email")
            login_password = st.text_input("Contraseña", type="password", key="login_password")
            
            if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                if login_email and login_password:
                    with st.spinner("Autenticando..."):
                        res = sign_in_user(login_email, login_password)
                        if res["success"]:
                            st.session_state["user"] = res["user"]
                            st.session_state["jwt_token"] = res["jwt_token"]
                            st.success("¡Sesión iniciada con éxito!")
                            st.session_state["projects"] = list_user_projects(res["jwt_token"])
                            if st.session_state["projects"]:
                                st.session_state["active_project"] = st.session_state["projects"][0]
                            st.rerun()
                        else:
                            st.error(f"Error de credenciales: {res['error']}")
                else:
                    st.warning("Por favor rellena todos los campos.")
                    
        with auth_tab2:
            st.subheader("Crear Cuenta Nueva")
            reg_email = st.text_input("Correo electrónico", key="reg_email")
            reg_password = st.text_input("Contraseña (mínimo 6 caracteres)", type="password", key="reg_password")
            reg_name = st.text_input("Nombre Completo", key="reg_name")
            reg_phone = st.text_input("Teléfono de Contacto", key="reg_phone")
            reg_rut = st.text_input("RUT (ej: 12.345.678-9)", key="reg_rut")
            reg_role = st.selectbox(
                "Rol del Usuario",
                options=["architect", "independent_developer", "engineering", "public_admin", "other"],
                format_func=lambda x: {
                    "architect": "Arquitecto",
                    "independent_developer": "Desarrollador Independiente",
                    "engineering": "Ingeniería / Constructor",
                    "public_admin": "Administración Pública (DOM)",
                    "other": "Otro"
                }[x]
            )
            
            if st.button("Registrarse", type="primary", use_container_width=True):
                if reg_email and reg_password and reg_name and reg_rut:
                    with st.spinner("Registrando..."):
                        res = sign_up_user(
                            email=reg_email,
                            password=reg_password,
                            name=reg_name,
                            phone=reg_phone,
                            rut=reg_rut,
                            role=reg_role
                        )
                        if res["success"]:
                            st.success("¡Registro completado! Ahora puedes iniciar sesión en la pestaña correspondiente.")
                        else:
                            st.error(f"Error al registrar: {res['error']}")
                else:
                    st.warning("Completa los campos obligatorios (Correo, Contraseña, Nombre y RUT).")

def render_create_project_form():
    st.subheader("Crear Nuevo Proyecto")
    st.markdown("Ingresa los datos normativos y de ubicación geográfica del terreno para aplicar el marco regulatorio correspondiente.")
    
    with st.form("create_project_form"):
        p_name = st.text_input("Nombre del Proyecto *", placeholder="Ej: Condominio Las Flores")
        p_type = st.selectbox(
            "Tipo de Proyecto *",
            options=["private_housing", "large_scale_real_estate", "public_spaces_green_areas", "other"],
            format_func=lambda x: {
                "private_housing": "Vivienda Privada (Unifamiliar/Condominios)",
                "large_scale_real_estate": "Inmobiliario de Gran Envergadura (Comercial, Industrial)",
                "public_spaces_green_areas": "Espacios Públicos y Áreas Verdes",
                "other": "Otro"
            }[x]
        )
        
        col1, col2 = st.columns(2)
        with col1:
            p_region = st.text_input("Región *", placeholder="Ej: Metropolitana de Santiago")
        with col2:
            p_commune = st.text_input("Comuna *", placeholder="Ej: Providencia")
            
        st.markdown("**Ubicación Geográfica (Coordenadas)**")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            p_lat = st.number_input("Latitud", format="%.8f", value=-33.4489)
        with col_c2:
            p_lng = st.number_input("Longitud", format="%.8f", value=-70.6693)
            
        st.markdown("**Identificación del Terreno (Catastral)**")
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            p_rol = st.text_input("Rol de Avalúo (Terreno)", placeholder="Ej: 1245-22")
        with col_t2:
            p_block = st.text_input("Manzana", placeholder="Ej: 14")
        with col_t3:
            p_lot = st.text_input("Lote", placeholder="Ej: A-3")
            
        submitted = st.form_submit_button("Guardar Proyecto", type="primary")
        
        if submitted:
            if p_name and p_region and p_commune:
                p_data = {
                    "name": p_name,
                    "project_type": p_type,
                    "region": p_region,
                    "commune": p_commune,
                    "latitude": p_lat,
                    "longitude": p_lng,
                    "terrain_rol": p_rol,
                    "block": p_block,
                    "lot": p_lot,
                    "user_id": st.session_state["user"].id
                }
                with st.spinner("Insertando proyecto..."):
                    res = create_project(p_data, st.session_state["jwt_token"])
                    if res["success"]:
                        st.success(f"Proyecto '{p_name}' creado con éxito.")
                        st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                        st.session_state["active_project"] = res["project"]
                        st.session_state["show_create_project"] = False
                        st.rerun()
                    else:
                        st.error(f"Error al guardar: {res['error']}")
            else:
                st.warning("Por favor, completa los campos obligatorios (*).")
                
    if st.button("Cancelar"):
        st.session_state["show_create_project"] = False
        st.rerun()

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

def display_results(result_data):
    st.success(f"Análisis normativo completado: **{result_data['project_name']}**")
    
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
            label="Estado",
            value="Aprobado con obs." if len(result_data.get("infractions", [])) > 0 else "Aprobado",
        )
        
    st.subheader("Resumen Ejecutivo (Consolidado por IA)", anchor=False)
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

def render_main_dashboard():
    st.sidebar.markdown('<div class="sidebar-title">Sesión Activa</div>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**{st.session_state['user'].email}**")
    
    role_mapping = {
        "architect": "Arquitecto",
        "independent_developer": "Desarrollador Indep.",
        "engineering": "Ingeniería / Const.",
        "public_admin": "Admin. Pública (DOM)",
        "other": "Usuario"
    }
    user_role = st.session_state["user"].user_metadata.get("role", "other")
    st.sidebar.markdown(f'<div class="user-badge">{role_mapping.get(user_role, "Usuario")}</div>', unsafe_allow_html=True)
    
    st.sidebar.divider()
    st.sidebar.markdown('<div class="sidebar-title">Proyectos</div>', unsafe_allow_html=True)
    
    projects_list = st.session_state["projects"]
    
    if projects_list:
        project_names = [p["name"] for p in projects_list]
        active_idx = 0
        if st.session_state["active_project"]:
            for i, p in enumerate(projects_list):
                if p["id"] == st.session_state["active_project"]["id"]:
                    active_idx = i
                    break
                    
        selected_project_name = st.sidebar.selectbox(
            "Seleccionar Proyecto Activo",
            options=project_names,
            index=active_idx
        )
        
        for p in projects_list:
            if p["name"] == selected_project_name:
                st.session_state["active_project"] = p
                break
    else:
        st.sidebar.warning("No tienes proyectos creados.")
        
    if st.sidebar.button("Crear Nuevo Proyecto", use_container_width=True):
        st.session_state["show_create_project"] = True
        st.rerun()
        
    st.sidebar.divider()
    
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["jwt_token"] = None
        st.session_state["active_project"] = None
        st.session_state["projects"] = []
        st.rerun()
        
    if st.session_state["show_create_project"]:
        render_create_project_form()
        return
        
    if not st.session_state["projects"]:
        st.title("¡Bienvenido a IANA!")
        st.info("Para comenzar a verificar tus archivos y planos de la OGUC, primero necesitas crear tu primer proyecto.")
        render_create_project_form()
        return
        
    p = st.session_state["active_project"]
    
    type_mapping = {
        "private_housing": "Vivienda Privada (Unifamiliar/Condominios)",
        "large_scale_real_estate": "Inmobiliario de Gran Envergadura (Comercial, Industrial)",
        "public_spaces_green_areas": "Espacios Públicos y Áreas Verdes",
        "other": "Otro"
    }
    
    st.markdown(
        f"""
        <div class="project-card">
            <div class="project-header">Proyecto: {p['name']}</div>
            <div class="project-meta">
                Ubicación: <b>{p['commune']}, {p['region']}</b> (Lat: {p['latitude'] or 'N/A'}, Lng: {p['longitude'] or 'N/A'}) <br>
                Tipo de Proyecto: <b>{type_mapping.get(p['project_type'], p['project_type'])}</b> | 
                ROL Terreno: <b>{p['terrain_rol'] or 'N/A'}</b> | Manzana: <b>{p['block'] or 'N/A'}</b> | Lote: <b>{p['lot'] or 'N/A'}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        st.metric(
            label="Cumplimiento Global del Proyecto",
            value=f"{float(p.get('success_probability', 0.0)):.1f}%"
        )
    with col_g2:
        st.markdown("**Contexto Consolidado del Proyecto (Memoria IA):**")
        st.caption(p.get("consolidated_context", "Aún no se han cargado documentos en este proyecto para consolidar un contexto."))

    st.divider()

    tab_val, tab_hist = st.tabs(["Validar Nuevo Documento", "Historial del Proyecto"])
    
    with tab_val:
        st.subheader("Subir Documentación del Proyecto", anchor=False)
        st.markdown("Sube planos, especificaciones técnicas (ETTs) o Certificados de Informaciones Previas (CIP) para verificar su cumplimiento normativo.")
        
        doc_type = st.selectbox(
            "Tipo de Documento a Subir",
            options=["cip", "ett", "site_plan", "sections", "elevations", "other"],
            format_func=lambda x: {
                "cip": "Certificado de Informaciones Previas (CIP)",
                "ett": "Especificaciones Técnicas de Trabajo (ETT)",
                "site_plan": "Plano de Emplazamiento General",
                "sections": "Plano de Cortes",
                "elevations": "Plano de Elevaciones",
                "other": "Otro Documento Complementario"
            }[x]
        )
        
        uploaded_file = st.file_uploader(
            "Selecciona el archivo PDF del proyecto:",
            type=["pdf"],
            help="El archivo debe tener texto seleccionable (no imágenes puras sin OCR)."
        )
        
        active_job_id = st.query_params.get("job_id")
        
        if uploaded_file is not None:
            st.info(f"Archivo listo: **{uploaded_file.name}** ({uploaded_file.size / 1024:.2f} KB)")
            
            if st.button("Iniciar Validación Normativa con IA", type="primary", use_container_width=True):
                job_id = str(uuid.uuid4())
                pdf_path = os.path.join(UPLOADS, f"{job_id}.pdf")
                
                with st.spinner("Procesando y almacenando archivo en Storage..."):
                    file_bytes = uploaded_file.getvalue()
                    
                    db_res = upload_project_document(
                        user_id=st.session_state["user"].id,
                        project_id=p["id"],
                        file_name=uploaded_file.name,
                        file_bytes=file_bytes,
                        document_type=doc_type,
                        jwt_token=st.session_state["jwt_token"]
                    )
                    
                    with open(pdf_path, "wb") as handle:
                        handle.write(file_bytes)
                        
                    if db_res.get("storage_location") == "local_fallback":
                        st.warning("No se pudo conectar con el storage remoto. El archivo se guardó localmente en modo fallback de emergencia y el análisis continuará normalmente.")
                    else:
                        st.success("Archivo guardado y respaldado en Supabase Storage con políticas RLS de seguridad.")

                with st.spinner("Extrayendo texto del PDF..."):
                    try:
                        blocks = extract_text_blocks(pdf_path)
                        plan_text = "\n".join([b.text for b in blocks])
                    except Exception as e:
                        st.error(f"Error al extraer texto del PDF: {e}")
                        st.stop()
                        
                if not plan_text.strip():
                    st.error("El PDF no contiene texto legible (sin capa OCR). Por favor sube un archivo procesable.")
                    st.stop()
                    
                with st.spinner("Realizando análisis individual de este documento (Gemini AI)..."):
                    try:
                        doc_analysis = evaluate_document_individually(
                            doc_text=plan_text,
                            doc_type=doc_type,
                            oguc_text=OGUC_CONTENT
                        )
                        
                        if db_res.get("success") and "document" in db_res:
                            doc_id = db_res["document"].get("id")
                            if doc_id:
                                try:
                                    save_document_analysis({
                                        "document_id": doc_id,
                                        "extracted_text_summary": doc_analysis.document_summary,
                                        "infractions": [inf.model_dump() for inf in doc_analysis.infractions],
                                        "metadata": doc_analysis.extracted_metadata
                                    }, st.session_state["jwt_token"])
                                except Exception as db_err:
                                    st.error(f"No se pudo guardar el análisis individual en la base de datos: {db_err}")
                    except Exception as e:
                        st.error(f"Error al analizar el documento: {e}")
                        st.stop()

                with st.spinner("Consolidando contexto histórico e integrando alertas..."):
                    try:
                        existing_context = p.get("consolidated_context", "") or "Proyecto inicializado."
                        existing_infractions = p.get("consolidated_infractions", []) or []
                        
                        consolidated = consolidate_project_context(
                            project_metadata=p,
                            existing_context=existing_context,
                            existing_infractions=existing_infractions,
                            new_doc_analysis=doc_analysis,
                            oguc_text=OGUC_CONTENT
                        )
                        
                        update_res = update_project_context_db(
                            project_id=p["id"],
                            context_data={
                                "consolidated_context": consolidated.consolidated_context,
                                "consolidated_infractions": [inf.model_dump() for inf in consolidated.consolidated_infractions],
                                "success_probability": consolidated.success_probability,
                                "extracted_metadata": consolidated.extracted_metadata,
                                "terrain_rol": consolidated.extracted_metadata.get("rol_terreno", p.get("terrain_rol")),
                                "block": consolidated.extracted_metadata.get("manzana", p.get("block")),
                                "lot": consolidated.extracted_metadata.get("lote", p.get("lot"))
                            },
                            jwt_token=st.session_state["jwt_token"]
                        )
                        
                        if update_res["success"]:
                            st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                            for updated_p in st.session_state["projects"]:
                                if updated_p["id"] == p["id"]:
                                    st.session_state["active_project"] = updated_p
                                    break
                        else:
                            st.error(f"Error al actualizar el contexto consolidado en la DB: {update_res['error']}")
                            
                    except Exception as e:
                        st.error(f"Error consolidando el contexto con IA: {e}")
                        st.stop()
                
                result_data = {
                    "job_id": job_id,
                    "filename": uploaded_file.name,
                    "project_name": p["name"],
                    "success_probability": consolidated.success_probability,
                    "infractions": [inf.model_dump() for inf in consolidated.consolidated_infractions],
                    "summary_notes": consolidated.consolidated_context,
                }
                
                out_json = os.path.join(RESULTS, f"{job_id}.json")
                with open(out_json, "w", encoding="utf-8") as handle:
                    json.dump(result_data, handle, ensure_ascii=False, indent=2)
                    
                out_html = os.path.join(RESULTS, f"{job_id}.html")
                with open(out_html, "w", encoding="utf-8") as handle:
                    handle.write(render_html_report(uploaded_file.name, result_data))
                    
                st.query_params["job_id"] = job_id
                st.rerun()
                
        if active_job_id:
            st.divider()
            path = os.path.join(RESULTS, f"{active_job_id}.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as handle:
                    result_data = json.load(handle)
                display_results(result_data)
            else:
                st.error("El análisis seleccionado no existe o fue eliminado.")
                
    with tab_hist:
        st.subheader("Archivos y Análisis Anteriores", anchor=False)
        history_jobs = get_jobs_history()
        
        if history_jobs:
            st.markdown("A continuación se listan las revisiones normativas realizadas:")
            for j in history_jobs:
                dt_str = datetime.fromtimestamp(j['mtime']).strftime('%Y-%m-%d %H:%M')
                col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                with col_h1:
                    st.markdown(f"**{j['filename']}** ({j['project_name']})")
                    st.caption(f"Revisado el {dt_str}")
                with col_h2:
                    st.metric("Viabilidad", f"{j['success_probability']:.1f}%")
                with col_h3:
                    st.markdown("")
                    st.markdown("")
                    if st.button("Ver Reporte", key=f"btn_{j['job_id']}", use_container_width=True):
                        st.query_params["job_id"] = j["job_id"]
                        st.rerun()
                st.divider()
        else:
            st.info("Aún no has realizado revisiones normativas para este proyecto. Sube un documento en la pestaña anterior para iniciar.")

if st.session_state["user"] is None:
    render_auth_page()
else:
    render_main_dashboard()