import streamlit as st
import os
import uuid
import json
import urllib.parse
from datetime import datetime

from app.version import __version__
from app.pdf_extract import extract_text_blocks
from app.ai_verifier import (
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
    update_project_context_db,
    list_project_documents,
    verify_jwt_session
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAVICON_PATH = os.path.join(os.path.dirname(BASE_DIR), "public", "favicon.ico")

st.set_page_config(
    page_title=f"IANA v{__version__} - Validador de Proyectos (OGUC)",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else None,
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
if "search_cache" not in st.session_state:
    st.session_state["search_cache"] = ""
if "limit" not in st.session_state:
    st.session_state["limit"] = 10
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Validar Nuevo Documento"
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = "file_uploader_v1"
if "docs_cache" not in st.session_state:
    st.session_state["docs_cache"] = None
if "history_cache" not in st.session_state:
    st.session_state["history_cache"] = None
if "viewing_pdf_id" not in st.session_state:
    st.session_state["viewing_pdf_id"] = None
if "cookie_to_set" not in st.session_state:
    st.session_state["cookie_to_set"] = None
if "cookie_to_clear" not in st.session_state:
    st.session_state["cookie_to_clear"] = False

if "chile_tz" not in st.session_state:
    try:
        from zoneinfo import ZoneInfo
        st.session_state["chile_tz"] = ZoneInfo("America/Santiago")
    except Exception:
        from datetime import timezone, timedelta
        st.session_state["chile_tz"] = timezone(timedelta(hours=-4))

def set_session_cookie(token: str):
    js = f"""
    <script>
    let cookieStr = "session_token={token}; path=/; max-age=2592000; SameSite=Lax";
    if (window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {{
        cookieStr += "; Secure";
    }}
    parent.document.cookie = cookieStr;
    </script>
    """
    st.components.v1.html(js, height=0, width=0)

def clear_session_cookie():
    js = """
    <script>
    let cookieStr = "session_token=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC; SameSite=Lax";
    if (window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        cookieStr += "; Secure";
    }
    parent.document.cookie = cookieStr;
    </script>
    """
    st.components.v1.html(js, height=0, width=0)

if st.session_state["cookie_to_set"]:
    set_session_cookie(st.session_state["cookie_to_set"])
    st.session_state["cookie_to_set"] = None

if st.session_state["cookie_to_clear"]:
    clear_session_cookie()
    st.session_state["cookie_to_clear"] = False

cookie_token = st.context.cookies.get("session_token")
if st.session_state["user"] is None and cookie_token:
    res = verify_jwt_session(cookie_token)
    if res["success"]:
        st.session_state["user"] = res["user"]
        st.session_state["jwt_token"] = cookie_token
        try:
            st.session_state["projects"] = list_user_projects(cookie_token)
            st.session_state["active_project"] = None
        except Exception as e:
            print(f"Error al restaurar proyectos tras recarga: {e}")

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
    
    .welcome-container {
        text-align: center;
        padding: 40px;
        max-width: 800px;
        margin: 0 auto;
    }
    .welcome-title {
        font-size: 36px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 15px;
    }
    .welcome-subtitle {
        font-size: 16px;
        color: #64748b;
        margin-bottom: 40px;
        line-height: 1.6;
    }
    .option-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
        margin-bottom: 15px;
    }
    .option-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    .option-icon {
        font-size: 40px;
        margin-bottom: 16px;
    }
    .option-title {
        font-size: 20px;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 8px;
    }
    .option-desc {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 20px;
        min-height: 60px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

REGION_COORDS = {
    "Arica y Parinacota": (-18.4783, -70.3126),
    "Tarapacá": (-20.2133, -70.1503),
    "Antofagasta": (-23.6509, -70.3975),
    "Atacama": (-27.3668, -70.3323),
    "Coquimbo": (-29.9533, -71.2436),
    "Valparaíso": (-33.0472, -71.6127),
    "Metropolitana de Santiago": (-33.4489, -70.6693),
    "Libertador General Bernardo O'Higgins": (-34.1708, -70.7444),
    "Maule": (-35.4264, -71.6554),
    "Ñuble": (-36.6074, -72.1030),
    "Bío Bío": (-36.8201, -73.0444),
    "Araucanía": (-38.7359, -72.5904),
    "Los Ríos": (-39.8142, -73.2459),
    "Los Lagos": (-41.4689, -72.9411),
    "Aysén del General Carlos Ibáñez del Campo": (-45.5712, -72.0685),
    "Magallanes y de la Antártica Chilena": (-53.1638, -70.9171)
}

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

@st.cache_data
def load_regions_and_communes():
    json_path = os.path.join(BASE_DIR, "knowledge", "regiones.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error cargando regiones y comunas: {e}")
    return {"regions": []}

def get_commune_coordinates(region_name: str, commune_name: str) -> tuple[float, float]:
    json_path = os.path.join(BASE_DIR, "knowledge", "regiones.json")
    data = None
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for r in data.get("regions", []):
                if r.get("name") == region_name:
                    for c in r.get("communes", []):
                        if c.get("name") == commune_name:
                            if "lat" in c and "lng" in c:
                                return float(c["lat"]), float(c["lng"])
    except Exception as e:
        print(f"Error al leer regiones.json para coordenadas: {e}")

    try:
        import httpx
        query = f"{commune_name}, {region_name}, Chile"
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"
        headers = {"User-Agent": f"IANA-App/{__version__}"}
        with httpx.Client(timeout=2.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                res_data = response.json()
                if res_data:
                    lat = float(res_data[0]["lat"])
                    lng = float(res_data[0]["lon"])
                    
                    lat = float(res_data[0]["lat"])
                    lng = float(res_data[0]["lon"])
                    return lat, lng
    except Exception as g_err:
        print(f"Fallo al geocodificar comuna {commune_name}: {g_err}")

    return REGION_COORDS.get(region_name, (-33.4489, -70.6693))

def get_document_file_bytes(doc: dict, jwt_token: str) -> bytes | None:
    bucket_path = doc.get("bucket_path", "")
    if not bucket_path:
        return None
        
    if bucket_path.startswith("local://fallback/"):
        filename = os.path.basename(bucket_path.replace("local://fallback/", ""))
        local_path = os.path.join(DATA_DIR, "uploads", "fallback", filename)
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    return f.read()
            except OSError as err:
                print(f"Error al leer archivo local de fallback: {err}")
    else:
        try:
            from app.db import get_supabase_client
            client = get_supabase_client(jwt_token)
            res = client.storage.from_("project-documents").download(bucket_path)
            return res
        except Exception as e:
            print(f"Error al descargar archivo desde Supabase Storage: {e}")
            
    return None

OGUC_CONTENT = load_oguc_in_memory()
if not OGUC_CONTENT:
    st.error("Error crítico: No se pudo cargar el archivo normativo OGUC_2026.md.")

def render_auth_page():
    st.title(f"IANA v{__version__} — Validador Normativo de Proyectos")
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
                            st.session_state["cookie_to_set"] = res["jwt_token"]
                            st.success("¡Sesión iniciada con éxito!")
                            st.session_state["projects"] = list_user_projects(res["jwt_token"])
                            st.session_state["active_project"] = None  # Landing page on login
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

@st.dialog("Crear Nuevo Proyecto", width="large")
def render_create_project_modal():
    st.markdown("Ingresa los datos normativos y de ubicación geográfica del terreno para aplicar el marco regulatorio correspondiente.")
    
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
    
    regions_data = load_regions_and_communes()
    region_names = [r["name"] for r in regions_data.get("regions", [])]
    
    col1, col2 = st.columns(2)
    with col1:
        p_region = st.selectbox("Región *", options=region_names if region_names else ["Metropolitana de Santiago"])
    with col2:
        commune_options = []
        if regions_data.get("regions"):
            for r in regions_data["regions"]:
                if r["name"] == p_region:
                    commune_options = [c["name"] for c in r.get("communes", [])]
                    break
        if not commune_options:
            commune_options = ["Providencia", "Santiago", "Las Condes"]
        p_commune = st.selectbox("Comuna *", options=commune_options)
        
    state_key_lat = f"lat_{p_region}_{p_commune}"
    state_key_lng = f"lng_{p_region}_{p_commune}"
    
    if state_key_lat not in st.session_state:
        lat_val, lng_val = get_commune_coordinates(p_region, p_commune)
        st.session_state[state_key_lat] = lat_val
        st.session_state[state_key_lng] = lng_val
        
    st.markdown("**Ubicación Geográfica (Coordenadas Estimadas)**")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        p_lat = st.number_input(
            "Latitud", 
            format="%.8f", 
            value=st.session_state[state_key_lat],
            key=f"input_{state_key_lat}"
        )
    with col_c2:
        p_lng = st.number_input(
            "Longitud", 
            format="%.8f", 
            value=st.session_state[state_key_lng],
            key=f"input_{state_key_lng}"
        )
        
    st.session_state[state_key_lat] = p_lat
    st.session_state[state_key_lng] = p_lng
        
    st.markdown("**Identificación del Terreno (Catastral - Opcional)**")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        p_rol = st.text_input("Rol de Avalúo (Terreno)", placeholder="Ej: 1245-22")
    with col_t2:
        p_block = st.text_input("Manzana", placeholder="Ej: 14")
    with col_t3:
        p_lot = st.text_input("Lote", placeholder="Ej: A-3")
        
    st.divider()
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn2:
        submitted = st.button("Guardar Proyecto", type="primary", use_container_width=True)
    with col_btn1:
        cancelled = st.button("Cancelar", use_container_width=True)
        
    if cancelled:
        st.rerun()
        
    if submitted:
        if p_name and p_region and p_commune:
            p_data = {
                "name": p_name,
                "project_type": p_type,
                "region": p_region,
                "commune": p_commune,
                "latitude": p_lat,
                "longitude": p_lng,
                "terrain_rol": p_rol if p_rol.strip() else None,
                "block": p_block if p_block.strip() else None,
                "lot": p_lot if p_lot.strip() else None,
                "user_id": st.session_state["user"].id
            }
            with st.spinner("Creando proyecto..."):
                res = create_project(p_data, st.session_state["jwt_token"])
                if res["success"]:
                    st.success(f"Proyecto '{p_name}' creado con éxito.")
                    st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                    st.session_state["active_project"] = res["project"]
                    st.rerun()
                else:
                    st.error(f"Error al guardar: {res['error']}")
        else:
            st.warning("Por favor, completa los campos obligatorios (*).")

@st.dialog("✏️ Editar Detalles del Proyecto", width="large")
def render_edit_project_modal():
    p = st.session_state["active_project"]
    if not p:
        st.warning("No hay un proyecto activo seleccionado.")
        return
        
    try:
        json_path = os.path.join(BASE_DIR, "knowledge", "regiones.json")
        with open(json_path, "r", encoding="utf-8") as f:
            regiones_data = json.load(f)
    except Exception:
        regiones_data = {"regions": []}
        
    regions = [r["name"] for r in regiones_data.get("regions", [])]
    
    p_name = st.text_input("Nombre del Proyecto *", value=p.get("name", ""))
    
    region_idx = regions.index(p["region"]) if p.get("region") in regions else 0
    p_region = st.selectbox("Región *", options=regions, index=region_idx, key="edit_region")
    
    communes = []
    region_sel = next((r for r in regiones_data.get("regions", []) if r["name"] == p_region), None)
    if region_sel:
        communes = [c["name"] for c in region_sel.get("communes", [])]
        
    commune_idx = communes.index(p["commune"]) if p.get("commune") in communes else 0
    p_commune = st.selectbox("Comuna *", options=communes, index=commune_idx, key="edit_commune")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        p_lat = st.number_input("Latitud", format="%.8f", value=float(p.get("latitude") or 0.0), key="edit_lat")
    with col_c2:
        p_lng = st.number_input("Longitud", format="%.8f", value=float(p.get("longitude") or 0.0), key="edit_lng")
        
    st.markdown("**Identificación del Terreno (Catastral - Opcional)**")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        p_rol = st.text_input("Rol de Avalúo (Terreno)", value=p.get("terrain_rol") or "", placeholder="Ej: 1245-22")
    with col_t2:
        p_block = st.text_input("Manzana", value=p.get("block") or "", placeholder="Ej: 14")
    with col_t3:
        p_lot = st.text_input("Lote", value=p.get("lot") or "", placeholder="Ej: A-3")
        
    st.divider()
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn2:
        submitted = st.button("Guardar Cambios", type="primary", use_container_width=True)
    with col_btn1:
        cancelled = st.button("Cancelar", use_container_width=True, key="btn_cancel_edit")
        
    if cancelled:
        st.rerun()
        
    if submitted:
        if p_name and p_region and p_commune:
            lat_val = p_lat
            lng_val = p_lng
            if (p_commune != p["commune"] or p_region != p["region"]) and (p_lat == p["latitude"] and p_lng == p["longitude"]):
                calc_lat, calc_lng = get_commune_coordinates(p_region, p_commune)
                lat_val = calc_lat
                lng_val = calc_lng
                
            update_data = {
                "name": p_name,
                "region": p_region,
                "commune": p_commune,
                "latitude": lat_val,
                "longitude": lng_val,
                "terrain_rol": p_rol if p_rol.strip() else None,
                "block": p_block if p_block.strip() else None,
                "lot": p_lot if p_lot.strip() else None
            }
            
            with st.spinner("Guardando cambios..."):
                res = update_project_context_db(p["id"], update_data, st.session_state["jwt_token"])
                if res["success"]:
                    st.success("Proyecto actualizado con éxito.")
                    st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                    for updated_p in st.session_state["projects"]:
                        if updated_p["id"] == p["id"]:
                            st.session_state["active_project"] = updated_p
                            break
                    st.rerun()
                else:
                    st.error(f"Error al guardar: {res['error']}")
        else:
            st.warning("Por favor, completa los campos obligatorios (*).")

def get_jobs_history(project_id: str):
    if not os.path.exists(RESULTS):
        return []
    try:
        files = [f for f in os.listdir(RESULTS) if f.endswith(".json")]
    except OSError as err:
        print(f"Error al listar archivos de resultados locales: {err}")
        return []
        
    history = []
    for f in files:
        path = os.path.join(RESULTS, f)
        try:
            mtime = os.path.getmtime(path)
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if data.get("user_id") == st.session_state["user"].id:
                has_match = False
                if "project_id" in data:
                    has_match = (data["project_id"] == project_id)
                else:
                    has_match = (data.get("project_name") == st.session_state["active_project"]["name"])
                
                if has_match:
                    history.append({
                        "job_id": data.get("job_id"),
                        "filename": data.get("filename"),
                        "project_name": data.get("project_name", data.get("filename")),
                        "success_probability": data.get("success_probability", 0.0),
                        "mtime": mtime
                    })
        except (OSError, ValueError) as err:
            print(f"Error leyendo archivo de historial local {path}: {err}")
            
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
            
            with st.expander(f"[{severity}] {inf.get('rule_id')} - {inf.get('description')[:80]}..."):
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
            label="Descargar Reporte HTML",
            data=html_content,
            file_name=f"reporte_iana_{result_data['job_id']}.html",
            mime="text/html",
            use_container_width=True
        )
    with col_d2:
        if pdf_content:
            st.download_button(
                label="Descargar Reporte PDF",
                data=pdf_content,
                file_name=f"reporte_iana_{result_data['job_id']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.button("Reporte PDF no disponible", disabled=True, use_container_width=True)

def render_main_dashboard():
    st.sidebar.markdown(f"**{st.session_state['user'].email}**")
    
    role_mapping = {
        "architect": "Arquitecto",
        "independent_developer": "Desarrollador Independiente",
        "engineering": "Ingeniería / Construcción",
        "public_admin": "Admin. Pública (DOM)",
        "other": "Usuario"
    }
    user_role = st.session_state["user"].user_metadata.get("role", "other")
    st.sidebar.markdown(f'<div class="user-badge">{role_mapping.get(user_role, "Usuario")}</div>', unsafe_allow_html=True)
    
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["jwt_token"] = None
        st.session_state["active_project"] = None
        st.session_state["projects"] = []
        st.session_state["cookie_to_clear"] = True
        st.rerun()
        
    st.sidebar.divider()
    st.sidebar.markdown('<div class="sidebar-title">Proyectos</div>', unsafe_allow_html=True)
    
    if st.sidebar.button("Crear Nuevo Proyecto", use_container_width=True, type="primary"):
        render_create_project_modal()
        
    st.sidebar.write("")
    
    p_search = st.sidebar.text_input("Buscar proyecto", key="project_search_input", placeholder="Filtrar por nombre...")
    
    projects_list = st.session_state["projects"]
    if projects_list:
        filtered_projects = projects_list
        if p_search.strip():
            filtered_projects = [p for p in projects_list if p_search.lower() in p["name"].lower()]
            
        if filtered_projects:
            for p_item in filtered_projects:
                is_active = (st.session_state["active_project"] and st.session_state["active_project"]["id"] == p_item["id"])
                btn_type = "primary" if is_active else "secondary"
                if st.sidebar.button(p_item["name"], key=f"sidebar_proj_{p_item['id']}", type=btn_type, use_container_width=True):
                    st.session_state["active_project"] = p_item
                    st.session_state["docs_cache"] = None
                    st.session_state["history_cache"] = None
                    st.session_state["viewing_pdf_id"] = None
                    st.rerun()
        else:
            st.sidebar.caption("No se encontraron proyectos.")
    else:
        st.sidebar.warning("No tienes proyectos creados.")
        
    st.sidebar.markdown(f'<div style="font-size: 11px; color: #94a3b8; text-align: center; margin-top: 50px;">IANA v{__version__}</div>', unsafe_allow_html=True)
        
    if not st.session_state["projects"] or st.session_state["active_project"] is None:
        st.markdown(
            f"""
            <div class="welcome-container">
                <div class="welcome-title">Bienvenido a IANA v{__version__}</div>
                <div class="welcome-subtitle">
                    La plataforma inteligente para validar el cumplimiento de la Ordenanza General de Urbanismo y Construcción (OGUC) de Chile de manera incremental y automatizada.
                    <br><br><b>Selecciona un proyecto existente en la barra lateral izquierda o crea uno nuevo para comenzar.</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_w1, col_w2 = st.columns(2)
        
        with col_w1:
            st.markdown(
                """
                <div class="option-card">
                    <div class="option-title">Crear tu Primer Proyecto</div>
                    <div class="option-desc">
                        Crea un proyecto asociando ubicación, tipo de obra y coordenadas geográficas para comenzar a subir planos, especificaciones (ETT) y certificados (CIP).
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Comenzar Nuevo Proyecto", type="primary", use_container_width=True):
                render_create_project_modal()
                
        with col_w2:
            st.markdown(
                """
                <div class="option-card">
                    <div class="option-title">Explorar Normativa OGUC</div>
                    <div class="option-desc">
                        Visualiza los artículos y regulaciones vigentes cargados en la base de conocimientos de IANA, que sirven de referencia para las revisiones normativas.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Ver Base Normativa", use_container_width=True):
                st.info("La normativa OGUC_2026.md está activa en memoria para el validador normativo de la IA.")
                with st.expander("Visualizar contenido cargado de la OGUC"):
                    st.text_area("Contenido OGUC", OGUC_CONTENT[:10000] + "\n\n... (contenido restante cargado en memoria)", height=300)
                    
        return
        
    p = st.session_state["active_project"]
    
    if p:
        if st.session_state["docs_cache"] is None:
            st.session_state["docs_cache"] = list_project_documents(p["id"], st.session_state["jwt_token"])
        if st.session_state["history_cache"] is None:
            st.session_state["history_cache"] = get_jobs_history(p["id"])
    
    type_mapping = {
        "private_housing": "Vivienda Privada (Unifamiliar/Condominios)",
        "large_scale_real_estate": "Inmobiliario de Gran Envergadura (Comercial, Industrial)",
        "public_spaces_green_areas": "Espacios Públicos y Áreas Verdes",
        "other": "Otro"
    }
    
    col_p1, col_p2 = st.columns([4, 1])
    with col_p1:
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
    with col_p2:
        st.write("")
        st.write("")
        if st.button("Editar Proyecto", use_container_width=True):
            render_edit_project_modal()
            
    docs = st.session_state["docs_cache"] or []
    uploaded_types = {d["document_type"] for d in docs}
    
    missing_docs = []
    if "cip" not in uploaded_types:
        missing_docs.append("Certificado de Informaciones Previos (CIP)")
    if "ett" not in uploaded_types:
        missing_docs.append("Especificaciones Técnicas (ETT)")
        
    missing_planos = []
    if "site_plan" not in uploaded_types:
        missing_planos.append("Emplazamiento General")
    if "sections" not in uploaded_types:
        missing_planos.append("Cortes")
    if "elevations" not in uploaded_types:
        missing_planos.append("Elevaciones")
        
    if missing_planos:
        missing_docs.append(f"Planos ({', '.join(missing_planos)})")
        
    if missing_docs:
        missing_str = ", ".join(missing_docs)
        st.warning(
            f"Falta subir los siguientes documentos obligatorios para este proyecto: {missing_str}. "
            "Es necesario cargarlos para obtener el número de ROL de terreno, manzana y lote."
        )
        
    st.write("")

    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "Validar Nuevo Documento"
    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = "file_uploader_init"

    tab_options = ["Validar Nuevo Documento", "Documentos Asociados", "Historial de Aprobación"]
    active_idx = tab_options.index(st.session_state["active_tab"]) if st.session_state["active_tab"] in tab_options else 0
    
    selected_tab = st.radio(
        "Navegación",
        options=tab_options,
        index=active_idx,
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state["active_tab"] = selected_tab
    
    st.write("")
    
    if st.session_state["active_tab"] == "Validar Nuevo Documento":
        st.subheader("Subir Documentación del Proyecto", anchor=False)
        st.markdown("Sube planos, especificaciones técnicas (ETTs) o Certificados de Informaciones Previas (CIP) para verificar su cumplimiento normativo.")
        
        doc_type = st.selectbox(
            "Tipo de Documento a Subir",
            options=["cip", "ett", "site_plan", "sections", "elevations", "other"],
            format_func=lambda x: {
                "cip": "Certificado de Informaciones Previos (CIP)",
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
            key=st.session_state["file_uploader_key"],
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
                    "user_id": st.session_state["user"].id,
                    "project_id": p["id"],
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
                    
                st.session_state["file_uploader_key"] = f"file_uploader_{uuid.uuid4()}"
                st.session_state["docs_cache"] = None
                st.session_state["history_cache"] = None
                st.query_params["job_id"] = job_id
                st.rerun()
                
        if active_job_id:
            st.divider()
            path = os.path.join(RESULTS, f"{active_job_id}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        result_data = json.load(handle)
                    if result_data.get("user_id") == st.session_state["user"].id:
                        display_results(result_data)
                    else:
                        st.error("No tienes autorización para ver este reporte.")
                except (OSError, ValueError) as err:
                    st.error(f"Error cargando el archivo de resultados: {err}")
            else:
                st.error("El análisis seleccionado no existe o fue eliminado.")
                
    elif st.session_state["active_tab"] == "Documentos Asociados":
        st.subheader("Documentos Asociados al Proyecto", anchor=False)
        st.markdown("Lista de planos y especificaciones técnicas oficiales cargados en este proyecto:")
        
        DOC_TYPE_LABELS = {
            "cip": "Certificado de Informaciones Previos (CIP)",
            "ett": "Especificaciones Técnicas de Trabajo (ETT)",
            "site_plan": "Plano de Emplazamiento General",
            "sections": "Plano de Cortes",
            "elevations": "Plano de Elevaciones",
            "other": "Otro Documento Complementario"
        }
        
        docs = st.session_state["docs_cache"] or []
        if docs:
            for d in docs:
                dt_str = ""
                if d.get("created_at"):
                    try:
                        dt_obj = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
                        dt_chile = dt_obj.astimezone(st.session_state["chile_tz"])
                        dt_str = dt_chile.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        dt_str = str(d["created_at"])[:16]
                        
                col_d1, col_d2, col_d3 = st.columns([3, 2, 1])
                with col_d1:
                    st.markdown(f"**{d.get('file_name')}**")
                    st.caption(f"Subido el {dt_str}")
                with col_d2:
                    doc_type_raw = d.get("document_type", "other")
                    st.markdown(f"**Tipo:** {DOC_TYPE_LABELS.get(doc_type_raw, doc_type_raw)}")
                with col_d3:
                    if st.button("Ver", key=f"view_assoc_pdf_{d.get('id')}", use_container_width=True):
                        st.session_state["viewing_pdf_id"] = d.get("id")
                        st.rerun()
                st.divider()
                
            viewing_id = st.session_state.get("viewing_pdf_id")
            if viewing_id:
                selected_doc = next((doc for doc in docs if doc["id"] == viewing_id), None)
                if selected_doc:
                    st.subheader(f"Visualizador: {selected_doc.get('file_name')}", anchor=False)
                    
                    with st.spinner("Cargando archivo PDF..."):
                        file_bytes = get_document_file_bytes(selected_doc, st.session_state["jwt_token"])
                        
                    if file_bytes:
                        col_ctrl1, col_ctrl2 = st.columns([1, 1])
                        with col_ctrl1:
                            st.download_button(
                                label="Descargar PDF original",
                                data=file_bytes,
                                file_name=selected_doc.get("file_name"),
                                mime="application/pdf",
                                key="dl_viewing_pdf",
                                use_container_width=True
                            )
                        with col_ctrl2:
                            if st.button("Cerrar Visualizador", use_container_width=True):
                                st.session_state["viewing_pdf_id"] = None
                                st.rerun()
                                
                        import base64
                        try:
                            base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" style="border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 15px;"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error al renderizar el visualizador PDF: {e}")
                    else:
                        st.error("No se pudo obtener el archivo de este documento en el almacenamiento.")
                        if st.button("Cerrar", use_container_width=True):
                            st.session_state["viewing_pdf_id"] = None
                            st.rerun()
        else:
            st.info("Aún no se han subido documentos a este proyecto. Ve a la pestaña 'Validar Nuevo Documento' para subir tu primer plano o ETT.")
            
    else:
        st.subheader("Historial de Aprobación del Proyecto", anchor=False)
        history_jobs = st.session_state["history_cache"] or []
        
        if history_jobs:
            st.markdown("Línea de tiempo de evaluaciones normativas y cambios en el porcentaje de aprobación del proyecto:")
            
            history_sorted = sorted(history_jobs, key=lambda x: x["mtime"])
            
            deltas = {}
            prev_prob = None
            for idx, job in enumerate(history_sorted):
                curr_prob = job["success_probability"]
                if prev_prob is None:
                    delta = None
                else:
                    delta = curr_prob - prev_prob
                deltas[job["job_id"]] = delta
                prev_prob = curr_prob
                
            history_recent = list(reversed(history_sorted))
            
            for job in history_recent:
                dt = datetime.fromtimestamp(job['mtime'], tz=st.session_state["chile_tz"])
                dt_str = dt.strftime('%Y-%m-%d %H:%M')
                delta_val = deltas.get(job["job_id"])
                
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.markdown(f"**Archivo Subido:** `{job['filename']}`")
                    st.caption(f"Evaluación realizada el {dt_str}")
                with col_h2:
                    if delta_val is None:
                        st.metric(
                            label="Viabilidad", 
                            value=f"{job['success_probability']:.1f}%",
                            help="Porcentaje inicial del proyecto"
                        )
                    elif delta_val == 0:
                        st.metric(
                            label="Viabilidad",
                            value=f"{job['success_probability']:.1f}%",
                            delta="+0.0%",
                            delta_color="off"
                        )
                    else:
                        st.metric(
                            label="Viabilidad", 
                            value=f"{job['success_probability']:.1f}%",
                            delta=f"{delta_val:+.1f}%",
                            delta_color="normal" if delta_val > 0 else "inverse"
                        )
                st.divider()
        else:
            st.info("Aún no se han registrado evaluaciones normativas para este proyecto. Sube un documento en la pestaña 'Validar Nuevo Documento' para comenzar.")

    st.divider()
    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        st.metric(
            label="Cumplimiento Global del Proyecto",
            value=f"{float(p.get('success_probability', 0.0)):.1f}%"
        )
    with col_g2:
        st.markdown("**Contexto Consolidado del Proyecto (Memoria IA):**")
        st.caption(p.get("consolidated_context", "Aún no se han cargado documentos en este proyecto para consolidar un contexto."))

if st.session_state["user"] is None:
    render_auth_page()
else:
    render_main_dashboard()