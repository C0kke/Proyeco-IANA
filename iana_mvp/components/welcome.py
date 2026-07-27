import streamlit as st
from app.version import __version__
from components.dialogs import render_create_project_modal
from app.assets import get_asset_base64

def render_welcome_page(oguc_content: str):
    welcome_logo_b64 = get_asset_base64("logo_IANA_con_nombre.png")
    logo_html = f'<img src="{welcome_logo_b64}" alt="IANA Logo" class="welcome-logo-img" /><br>' if welcome_logo_b64 else ""

    st.markdown(
        f"""
        <div class="welcome-container">
            {logo_html}
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
                st.text_area("Contenido OGUC", oguc_content[:10000] + "\n\n... (contenido restante cargado en memoria)", height=300)