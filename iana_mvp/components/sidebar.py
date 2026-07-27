import streamlit as st
from app.version import __version__
from components.dialogs import render_create_project_modal
from app.assets import get_asset_base64

def render_sidebar():
    logo_sidebar_b64 = get_asset_base64("logo_iana.png")
    user_name = st.session_state["user"].user_metadata.get("name", st.session_state["user"].email)
    user_role = st.session_state["user"].user_metadata.get("role", "Usuario")
    
    logo_html = f'<img src="{logo_sidebar_b64}" alt="IANA Logo" class="sidebar-logo-img" /><br>' if logo_sidebar_b64 else ""

    profile_card_html = (
        f'<div class="sidebar-user-profile-card">'
        f'{logo_html}'
        f'<div class="sidebar-user-name">{user_name}</div>'
        f'<div class="user-badge">{user_role}</div>'
        f'</div>'
    )
    st.sidebar.markdown(profile_card_html, unsafe_allow_html=True)
    
    st.sidebar.markdown('<div class="sidebar-title">Proyectos</div>', unsafe_allow_html=True)
    
    if st.sidebar.button("Crear Nuevo Proyecto", use_container_width=True, type="primary", key="sidebar_create_proj_btn"):
        render_create_project_modal()
        
    p_search = st.sidebar.text_input(
        "Buscar proyecto", 
        key="project_search_input", 
        placeholder="Filtrar por nombre...", 
        label_visibility="collapsed"
    )
    
    with st.sidebar.container(key="sidebar_projects_container", height=270, border=False):
        projects_list = st.session_state["projects"]
        if projects_list:
            filtered_projects = projects_list
            if p_search.strip():
                filtered_projects = [p for p in projects_list if p_search.lower() in p["name"].lower()]
                
            if filtered_projects:
                for p_item in filtered_projects:
                    is_active = (st.session_state["active_project"] and st.session_state["active_project"]["id"] == p_item["id"])
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(
                        p_item["name"], 
                        key=f"sidebar_proj_{p_item['id']}", 
                        type=btn_type, 
                        use_container_width=True
                    ):
                        st.session_state["active_project"] = p_item
                        st.session_state["docs_cache"] = None
                        st.session_state["history_cache"] = None
                        st.session_state["viewing_pdf_id"] = None
                        st.session_state["active_tab"] = "Validar Nuevo Documento"
                        st.rerun()
            else:
                st.caption("No se encontraron proyectos.")
        else:
            st.warning("No tienes proyectos creados.")
    
    st.sidebar.markdown('<div class="sidebar-bottom-spacer"></div>', unsafe_allow_html=True)
    
    if st.sidebar.button("Cerrar Sesión", use_container_width=True, key="sidebar_logout_btn"):
        st.session_state["user"] = None
        st.session_state["jwt_token"] = None
        st.session_state["active_project"] = None
        st.session_state["projects"] = []
        st.session_state["projects_loaded"] = False
        st.session_state["cookie_to_clear"] = True
        st.session_state["logged_out"] = True
        st.rerun()
        
    st.sidebar.markdown(f'<div class="sidebar-version">IANA v{__version__}</div>', unsafe_allow_html=True)