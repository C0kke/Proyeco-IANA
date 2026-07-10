import streamlit as st
from app.version import __version__
from components.dialogs import render_create_project_modal

def render_sidebar():
    st.sidebar.markdown(f"**{st.session_state['user'].email}**")
    
    user_role = st.session_state["user"].user_metadata.get("role", "Usuario")
    st.sidebar.markdown(f'<div class="user-badge">{user_role}</div>', unsafe_allow_html=True)
    
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
                    st.session_state["active_tab"] = "Validar Nuevo Documento"
                    st.rerun()
        else:
            st.sidebar.caption("No se encontraron proyectos.")
    else:
        st.sidebar.warning("No tienes proyectos creados.")
        
    st.sidebar.markdown(f'<div style="font-size: 11px; color: #94a3b8; text-align: center; margin-top: 50px;">IANA v{__version__}</div>', unsafe_allow_html=True)