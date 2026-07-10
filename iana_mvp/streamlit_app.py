import streamlit as st
import os
from app.version import __version__
from app.db import verify_jwt_session, list_user_projects

from components.auth import render_auth_page
from components.sidebar import render_sidebar
from components.welcome import render_welcome_page
from components.project_dashboard import render_project_dashboard

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

st.session_state.setdefault("user", None)
st.session_state.setdefault("jwt_token", None)
st.session_state.setdefault("projects", [])
st.session_state.setdefault("active_project", None)
st.session_state.setdefault("search_cache", "")
st.session_state.setdefault("limit", 10)
st.session_state.setdefault("active_tab", "Validar Nuevo Documento")
st.session_state.setdefault("file_uploader_key", "file_uploader_v1")
st.session_state.setdefault("docs_cache", None)
st.session_state.setdefault("history_cache", None)
st.session_state.setdefault("viewing_pdf_id", None)
st.session_state.setdefault("cookie_to_set", None)
st.session_state.setdefault("cookie_to_clear", False)
st.session_state.setdefault("logged_out", False)

if "chile_tz" not in st.session_state:
    try:
        from zoneinfo import ZoneInfo
        st.session_state["chile_tz"] = ZoneInfo("America/Santiago")
    except Exception:
        from datetime import timezone, timedelta
        st.session_state["chile_tz"] = timezone(timedelta(hours=-4))

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
if st.session_state["user"] is None and cookie_token and not st.session_state["logged_out"]:
    res = verify_jwt_session(cookie_token)
    if res["success"]:
        st.session_state["user"] = res["user"]
        st.session_state["jwt_token"] = res["jwt_token"]
        if res.get("refreshed"):
            st.session_state["cookie_to_set"] = res["jwt_token"]
        try:
            st.session_state["projects"] = list_user_projects(res["jwt_token"])
            st.session_state["active_project"] = None
        except Exception as e:
            print(f"Error al restaurar proyectos tras recarga: {e}")

styles_path = os.path.join(os.path.dirname(__file__), "index.css")
if os.path.exists(styles_path):
    with open(styles_path, "r", encoding="utf-8") as f:
        custom_css = f.read()
    st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)

if st.session_state["user"] is None:
    render_auth_page()
else:
    render_sidebar()
    if st.session_state["active_project"] is None:
        render_welcome_page(OGUC_CONTENT)
    else:
        render_project_dashboard(OGUC_CONTENT, UPLOADS, RESULTS)