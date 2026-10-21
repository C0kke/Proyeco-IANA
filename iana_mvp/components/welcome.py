import streamlit as st
import os
import base64
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

    # Estado para controlar la visibilidad del visor normativo a ancho completo
    if "show_oguc_base" not in st.session_state:
        st.session_state["show_oguc_base"] = False

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
        if st.button("Comenzar Nuevo Proyecto", type="primary", use_container_width=True, key="btn_welcome_new_proj"):
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
        toggle_label = "Ocultar Base Normativa" if st.session_state["show_oguc_base"] else "Ver Base Normativa"
        if st.button(toggle_label, use_container_width=True, key="btn_toggle_oguc"):
            st.session_state["show_oguc_base"] = not st.session_state["show_oguc_base"]
            st.rerun()

    # SECCIÓN INFERIOR A ANCHO COMPLETO (Ubicada debajo de ambas tarjetas)
    if st.session_state["show_oguc_base"]:
        st.write("")
        st.divider()
        st.subheader("📖 Base Normativa Oficial OGUC (Octubre 2026)", anchor=False)
        st.info("La normativa **OGUC_2026.md** está activa en memoria RAM para el motor de Inteligencia Artificial.")

        tab_pdf, tab_md = st.tabs(["📄 Documento Oficial (PDF)", "📝 Lectura Formateada (Markdown)"])

        with tab_pdf:
            # Búsqueda dinámica de la ruta del PDF en la carpeta knowledge
            pdf_path = os.path.join(os.getcwd(), "knowledge", "OGUC-Octubre-2026.pdf")
            if not os.path.exists(pdf_path):
                pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledge", "OGUC-Octubre-2026.pdf"))

            if os.path.exists(pdf_path):
                try:
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()

                    col_dl, _ = st.columns([1, 2])
                    with col_dl:
                        st.download_button(
                            label="Descargar OGUC Octubre 2026 (PDF)",
                            data=pdf_bytes,
                            file_name="OGUC-Octubre-2026.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="dl_oguc_pdf_welcome"
                        )

                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700px" style="border: 1px solid #27272A; border-radius: 8px; margin-top: 10px;"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error al cargar el archivo PDF: {e}")
            else:
                st.warning("No se encontró el archivo `OGUC-Octubre-2026.pdf` en la carpeta `knowledge/`.")

        with tab_md:
            search_query = st.text_input("🔍 Buscar en la OGUC:", placeholder="Ej: Artículo 4.1.7, rasantes, distanciamientos...", key="search_oguc_md")
            
            if search_query.strip():
                lines = oguc_content.split("\n")
                matches = [line for line in lines if search_query.lower() in line.lower()]
                st.markdown(f"**Coincidencias encontradas:** `{len(matches)}` líneas")
                with st.container(height=450):
                    st.markdown("\n".join(matches[:150]))
            else:
                with st.container(height=500):
                    st.markdown(oguc_content)